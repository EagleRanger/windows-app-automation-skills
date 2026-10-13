import copy
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from check_title_transcription import check

class TitleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.doc=self.root/'test.docx'
        self.src=self.root/'evidence.png'
        self.src.write_bytes(b'fixture evidence only')
        self.data={'artifact':{},'expected_ids':['3-1-1'],'items':[{
            'id':'3-1-1','paragraph_index':0,'source_title':'关于工程涉河防洪影响情况意见的函',
            'source_evidence':self.ref(self.src),'source_reviewed':True,'source_locator':'fixture title',
            'review_note':'Synthetic fixture, not actual image recognition'}]}
        self.write('附件 3-1-1 关于工程涉河防洪影响情况意见的函')
    def ref(self,p): return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    def write(self,text,extra=''):
        with zipfile.ZipFile(self.doc,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r>'+extra+'<w:t>'+escape(text)+'</w:t></w:r></w:p></w:body></w:document>')
        self.data['artifact']=self.ref(self.doc)
    def test_exact(self): self.assertEqual(check(self.data)['status'],'transcription_matches')
    def test_space_only(self):
        self.write('附件 3 - 1 - 1 关于工程\n涉河防洪影响情况意见的函')
        self.assertEqual(check(self.data)['status'],'transcription_matches')
    def test_deleted_word(self):
        self.write('附件 3-1-1 关于工程防洪影响情况意见的函')
        self.assertEqual(check(self.data)['status'],'title_changes_required')
    def test_added_word(self):
        self.write('附件 3-1-1 关于项目工程涉河防洪影响情况意见的函')
        self.assertEqual(check(self.data)['status'],'title_changes_required')
    def test_reordered_words(self):
        self.write('附件 3-1-1 关于工程涉河防洪影响情况的意见')
        self.assertEqual(check(self.data)['status'],'title_changes_required')
    def test_punctuation_matters(self):
        self.write('附件 3-1-1 关于《工程》涉河防洪影响情况意见的函')
        self.assertEqual(check(self.data)['status'],'title_changes_required')
    def test_year_at_start(self):
        self.data['items'][0]['source_title']='2025年报告'
        self.write('附件 3-1-1 2025年报告')
        self.assertEqual(check(self.data)['status'],'transcription_matches')
    def test_wrong_label(self):
        self.write('附件 3-1-2 关于工程涉河防洪影响情况意见的函')
        with self.assertRaises(ValueError): check(self.data)
    def test_unreviewed(self):
        self.data['items'][0]['source_reviewed']=False
        with self.assertRaises(ValueError): check(self.data)
    def test_scope_missing(self):
        self.data['expected_ids'].append('3-1-2')
        with self.assertRaises(ValueError): check(self.data)
    def test_duplicate(self):
        self.data['items'].append(copy.deepcopy(self.data['items'][0]))
        with self.assertRaises(ValueError): check(self.data)
    def test_stale_source(self):
        self.src.write_bytes(b'changed')
        with self.assertRaises(ValueError): check(self.data)
    def test_stale_doc(self):
        self.data['artifact']['sha256']='0'*64
        with self.assertRaises(ValueError): check(self.data)
    def test_hidden_text(self):
        self.write('附件 3-1-1 关于工程涉河防洪影响情况意见的函','<w:rPr><w:vanish/></w:rPr>')
        with self.assertRaises(ValueError): check(self.data)

if __name__=='__main__': unittest.main(verbosity=2)
