"""Build-time only allowlisted asset retrieval and immutable runtime assembly."""
import re
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from hardcase.contracts import atomic_json, digest, file_digest, load_json, require
from hardcase.inference.bundle import Bundle


def safe_unpack(archive_path, destination):
    destination = Path(destination).resolve()
    with tarfile.open(archive_path, 'r:gz') as archive:
        total = 0
        members = archive.getmembers()
        require(len(members) <= 2000, 'ASSET_MEMBER_LIMIT')
        for member in members:
            target = (destination/member.name).resolve()
            require(target.is_relative_to(destination) and not member.name.startswith('/') and not member.issym() and not member.islnk() and (member.isfile() or member.isdir()), 'UNSAFE_DELIVERY_ARCHIVE')
            total += member.size
        require(total <= 1024**3, 'EXPANDED_ASSET_LIMIT')
        archive.extractall(destination, members=members, filter='data')


def package():
    request = load_json('requests/runtime.json')
    tag = request['release_tag']
    require(re.fullmatch(r'training-assets-[0-9]+', tag) is not None, 'UNAPPROVED_ASSET_TAG')
    require(re.fullmatch(r'[a-f0-9]{64}', request['asset_sha256']) is not None, 'INVALID_ASSET_DIGEST')
    require(request['variant'] in {'candidate_float32','candidate_int8'}, 'UNAPPROVED_VARIANT')
    with tempfile.TemporaryDirectory(prefix='hardcase-package-') as temp:
        temporary = Path(temp)
        archive_path = temporary/'serving-bundles.tar.gz'
        url = 'https://github.com/mekala27-45/hardcase/releases/download/'+tag+'/serving-bundles.tar.gz'
        with urllib.request.urlopen(url, timeout=60) as response, archive_path.open('wb') as output:
            total = 0
            while chunk := response.read(1024*1024):
                total += len(chunk)
                require(total <= 600*1024**2,'DOWNLOAD_LIMIT')
                output.write(chunk)
        require(file_digest(archive_path) == request['asset_sha256'], 'DELIVERY_HASH_MISMATCH')
        safe_unpack(archive_path, temporary/'expanded')
        exported = load_json(temporary/'expanded/artifacts/export/selection.json')
        require(exported['export_id'] == request['export_id'] and exported['variant'] == request['variant'], 'SERVING_SELECTION_CHANGED')
        destination = Path('runtime/bundles')
        require(not destination.exists(), 'RUNTIME_ALREADY_ASSEMBLED')
        destination.mkdir(parents=True)
        allowlist = []
        methods = list(dict.fromkeys(['base_float32', request['variant'], 'candidate_float32']))
        for method in methods:
            source = temporary/'expanded/artifacts/bundles'/method
            bundle = Bundle(source)
            require(bundle.id == exported['validation'][method]['bundle_id'], 'EXPORTED_ID_CHANGED')
            shutil.copytree(source, destination/method)
            allowlist.append({'directory': method, 'id': bundle.id, 'method': method})
            del bundle
        atomic_json(destination/'allowlist.json', {'bundles':allowlist,'export_id':exported['export_id'],'release_tag':tag,'asset_sha256':request['asset_sha256']})
        actual_bytes=sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
        atomic_json('runtime/package-receipt.json', {'bytes':actual_bytes,'bundles':allowlist,'request_digest':digest(request),'status':'verified_build_artifacts','live_verified':False})
        if Path('evidence/evaluation/report.json').exists():
            shutil.copy2('evidence/evaluation/report.json','runtime/report.json')
        print('Verified runtime bundle package:',actual_bytes,'bytes')


if __name__=='__main__':
    package()
