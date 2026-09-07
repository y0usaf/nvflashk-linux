import io
from pathlib import Path
import sys
import tempfile
import unittest

from no_write import dialogue, run

BEFORE = (b"PCI Subsystem ID override detected.\r\n"
          b'Type "YES" to confirm (all caps): ')
BOARD = (b"Overriding the PCI Subsystem ID mismatch.\r\n"
         b"Board ID override detected.\r\n"
         b'Type "YES" to confirm (all caps): ')
AFTER = (b"Overriding the Board ID mismatch.\r\n"
         b"Current: 95.02.47.00.01\r\nReplace with: 95.02.3C.40.40\r\n"
         b"Update display adapter firmware?\r\n"
         b"Press 'y' to confirm (any other key to abort): ")


class NoWriteTests(unittest.TestCase):
    def fake(self, directory, first=BEFORE, second=BOARD, third=AFTER, stall=False):
        script = Path(directory) / "fake.py"
        record = Path(directory) / "inputs"
        script.write_text(
            "import os,sys,time\n"
            f"f=open({str(record)!r},'wb',buffering=0)\n"
            f"first={first!r}\n"
            "for b in first: os.write(1,bytes([b]))\n"
            "a=sys.stdin.buffer.readline(); f.write(a)\n"
            "if a == b'YES\\n':\n"
            f" os.write(1,{second!r})\n"
            " a=sys.stdin.buffer.readline(); f.write(a)\n"
            " if a == b'YES\\n':\n"
            f"  os.write(1,{third!r})\n"
            "  a=open('/dev/tty','rb',buffering=0).readline(); f.write(a)\n"
            " if a not in (b'',b'n\\n'): raise SystemExit('UNSAFE INPUT')\n"
            + ("time.sleep(10)\n" if stall else "os.write(1,b'\\r\\nNothing changed!\\r\\n')\n")
        )
        return [sys.executable, str(script)], record

    def test_four_stages_never_send_write_confirmation(self):
        for before, board, after, expected in [(None, None, None, b""), (BEFORE, None, None, b"YES\n"),
                (BEFORE, BOARD, None, b"YES\nYES\n"), (BEFORE, BOARD, AFTER, b"YES\nYES\nn\n")]:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as d:
                command, record = self.fake(d)
                result = run(command, io.BytesIO(), before, after, timeout=3, board=board)
                self.assertIn(b"Nothing changed!", result)
                self.assertEqual(record.read_bytes(), expected)

    def test_drift_before_override_sends_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            command, record = self.fake(d, first=b"UNEXPECTED PROMPT")
            with self.assertRaisesRegex(ValueError, "drift"):
                run(command, io.BytesIO(), BEFORE, AFTER, timeout=3, board=BOARD)
            self.assertEqual(record.read_bytes(), b"")

    def test_drift_after_override_sends_no_more_input(self):
        with tempfile.TemporaryDirectory() as d:
            command, record = self.fake(d, second=b"UNEXPECTED PROMPT")
            with self.assertRaisesRegex(ValueError, "drift"):
                run(command, io.BytesIO(), BEFORE, AFTER, timeout=3, board=BOARD)
            self.assertEqual(record.read_bytes(), b"YES\n")

    def test_drift_at_final_prompt_sends_no_final_answer(self):
        with tempfile.TemporaryDirectory() as d:
            command, record = self.fake(d, third=b"UNEXPECTED FINAL PROMPT")
            with self.assertRaisesRegex(ValueError, "drift"):
                run(command, io.BytesIO(), BEFORE, AFTER, timeout=3, board=BOARD)
            self.assertEqual(record.read_bytes(), b"YES\nYES\n")

    def test_timeout_kills_child(self):
        with tempfile.TemporaryDirectory() as d:
            command, _ = self.fake(d, stall=True)
            with self.assertRaisesRegex(ValueError, "Timeout"):
                run(command, io.BytesIO(), timeout=0.5)

    def test_eof_before_prompt_fails(self):
        with self.assertRaisesRegex(ValueError, "EOF"):
            run([sys.executable, "-c", "pass"], io.BytesIO(), BEFORE, AFTER, timeout=3, board=BOARD)

    def test_reordered_or_wrong_identity_dialogue_rejected(self):
        for before, after in [(AFTER, BEFORE), (BEFORE, AFTER.replace(b"95.02.3C.40.40", b"OTHER")),
                              (BEFORE, AFTER + BEFORE)]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                dialogue(before, after, BOARD)


if __name__ == "__main__":
    unittest.main()
