import json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from finalize_round2_stream import finalize
class FinalizationTests(unittest.TestCase):
    def test_transaction_and_deadline(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);(p/'samples.raw').write_text('0: x:0;\n1: x:1;\n2: x:2;\n3: x:3;')
            records=[]
            for idx,complete in [(0,899.9),(1,900.0),(2,900.1)]:
                records += [dict(kind='prepare',raw_index=idx,formal_index=0 if idx==0 else 1,legal=True,duplicate=False),dict(kind='commit',raw_index=idx,timely=True),dict(kind='confirm',raw_index=idx,timely=True,commit_complete=complete)]
            (p/'sample_receipts.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
            result=finalize(p,900,100);self.assertEqual(result['formal_count'],1);self.assertEqual((p/'samples.formal').read_text(),'0: x:0;\n');self.assertEqual([r['reason'] for r in result['omitted']],['late','late','incomplete_transaction'])
    def test_empty_output_retained(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);(p/'samples.raw').touch();(p/'sample_receipts.jsonl').touch();self.assertEqual(finalize(p)['formal_count'],0);self.assertEqual((p/'samples.formal').read_bytes(),b'')
    def test_incomplete_receipt_not_committed(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);(p/'samples.raw').write_text('0: x:0;\n');(p/'sample_receipts.jsonl').write_text('{"kind":"prepare","raw_index":0}\n{"kind":')
            self.assertEqual(finalize(p)['formal_count'],0)
if __name__=='__main__':unittest.main()
