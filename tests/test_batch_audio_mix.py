import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "batch_runner.py")
spec = importlib.util.spec_from_file_location("batch_runner", MODULE_PATH)
batch_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch_runner)


class BatchAudioMixTests(unittest.TestCase):
    def test_batch_runner_accepts_alternate_csv_path(self):
        with patch('sys.argv', [
            'batch_runner.py', '--csv', 'examples/feynman_20_video_batch.csv',
            '--quality', 'draft',
        ]):
            args = batch_runner.parse_args()

        self.assertEqual(
            args.csv,
            Path('examples/feynman_20_video_batch.csv'),
        )
        self.assertEqual(args.quality, 'draft')

    def test_silent_audio_uses_target_video_duration(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            batch_runner, 'TEMP_AUDIO', Path(tmpdir),
        ):
            _, _, duration = batch_runner._make_silent_audio(
                {'target_duration_sec': '3'}, 'duration_test',
            )

        self.assertEqual(duration, 3.0)

    def test_raw_render_cues_are_mixed_with_voice_and_pad(self):
        with patch.object(
            batch_runner.subprocess,
            "check_output",
            side_effect=[b"30/1", b"0\n"],
        ), patch.object(batch_runner.subprocess, "run") as run:
            batch_runner.stitch_av(
                Path("raw.mp4"), Path("voice.wav"), Path("pad.wav"),
                Path("final.mp4"),
            )

        command = run.call_args.args[0]
        filter_complex = command[command.index("-filter_complex") + 1]
        self.assertIn("[0:a]volume=0.35[fx]", filter_complex)
        self.assertIn("[bed][fx]amix=inputs=2", filter_complex)
        self.assertIn("-map", command)
        self.assertIn("[aout]", command)

    def test_silent_raw_render_keeps_voice_and_pad_mix_valid(self):
        with patch.object(
            batch_runner.subprocess,
            "check_output",
            side_effect=[b"30/1", b""],
        ), patch.object(batch_runner.subprocess, "run") as run:
            batch_runner.stitch_av(
                Path("raw.mp4"), Path("voice.wav"), Path("pad.wav"),
                Path("final.mp4"),
            )

        filter_complex = run.call_args.args[0][
            run.call_args.args[0].index("-filter_complex") + 1
        ]
        self.assertIn("[bed]anull[amix]", filter_complex)


if __name__ == "__main__":
    unittest.main()