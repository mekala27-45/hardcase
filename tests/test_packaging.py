import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from deploy.package_runtime import safe_unpack


class PackagingTests(unittest.TestCase):
    def archive(self, path, name, link=False):
        with tarfile.open(path,'w:gz') as archive:
            member=tarfile.TarInfo(name)
            if link:
                member.type=tarfile.SYMTYPE
                member.linkname='/etc/passwd'
                archive.addfile(member)
            else:
                member.size=4
                archive.addfile(member,io.BytesIO(b'test'))

    def test_parent_escape_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'bad.tar.gz'
            self.archive(path,'../escaped')
            with self.assertRaisesRegex(ValueError,'UNSAFE'):
                safe_unpack(path,Path(root)/'output')

    def test_link_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'link.tar.gz'
            self.archive(path,'model.onnx',True)
            with self.assertRaisesRegex(ValueError,'UNSAFE'):
                safe_unpack(path,Path(root)/'output')

    def test_bounded_file_extracted(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'good.tar.gz'
            self.archive(path,'artifacts/model.onnx')
            safe_unpack(path,Path(root)/'output')
            self.assertEqual((Path(root)/'output/artifacts/model.onnx').read_bytes(),b'test')
