import os
import shutil
import tarfile
from pathlib import Path
from hardcase.contracts import atomic_json, digest, file_digest, load_json, require


def preserve():
    destination = Path('evidence/training')
    destination.mkdir(parents=True, exist_ok=True)
    for category in ('training', 'export'):
        source = Path('artifacts') / category
        for path in source.rglob('*'):
            if path.is_file() and path.suffix in ('.json', '.jsonl') and not any(p.startswith('checkpoint-') for p in path.parts):
                target = Path('evidence') / category / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    atomic_json(destination / 'terminal.json', {'status': os.environ['JOB_STATUS'], 'run_id': os.environ['GITHUB_RUN_ID'], 'source_commit': os.environ['GITHUB_SHA'], 'test_access': False})
    if not Path('artifacts/training/selection.json').exists():
        return
    package = Path('artifacts/delivery')
    package.mkdir(parents=True, exist_ok=True)
    selection = load_json('artifacts/training/selection.json')
    inventory = []
    for arm in selection['arms']:
        checkpoint = Path(arm['checkpoint'])
        target = package / (arm['arm'] + '.tar.gz')
        with tarfile.open(target, 'w:gz') as archive:
            archive.add(checkpoint, arcname=str(checkpoint))
        inventory.append({'name': target.name, 'sha256': file_digest(target), 'bytes': target.stat().st_size, 'checkpoint_manifest': arm['manifest_digest']})
    if Path('artifacts/export/selection.json').exists():
        target = package / 'serving-bundles.tar.gz'
        with tarfile.open(target, 'w:gz') as archive:
            archive.add('artifacts/bundles', arcname='artifacts/bundles')
            archive.add('artifacts/export', arcname='artifacts/export', filter=lambda item: None if item.name.endswith('.onnx') else item)
        inventory.append({'name': target.name, 'sha256': file_digest(target), 'bytes': target.stat().st_size})
    require(all(item['bytes'] < 1024**3 for item in inventory), 'DELIVERY_ASSET_TOO_LARGE')
    atomic_json(destination / 'delivery.json', {'selection_id': selection['selection_id'], 'assets': inventory, 'release_tag': 'training-assets-' + os.environ['GITHUB_RUN_ID'], 'status': 'packaged_not_yet_uploaded'})
    shutil.copy2(destination / 'delivery.json', package / 'delivery.json')


if __name__ == '__main__':
    preserve()
