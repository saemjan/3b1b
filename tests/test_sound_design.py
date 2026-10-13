import importlib.util
import os
import wave
import unittest


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "sound_design.py")
spec = importlib.util.spec_from_file_location("sound_design", MODULE_PATH)
sound_design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sound_design)


class SoundDesignTests(unittest.TestCase):
    def test_known_cues_create_valid_audio_and_reach_scene(self):
        class SceneStub:
            def __init__(self):
                self.sounds = []

            def add_sound(self, path, **kwargs):
                self.sounds.append((path, kwargs))

        scene = SceneStub()
        for cue in ("tick", "whoosh", "drone", "chime"):
            self.assertTrue(sound_design.add(scene, cue, gain_db=-12))

        self.assertEqual(len(scene.sounds), 4)
        for path, options in scene.sounds:
            with wave.open(path, "rb") as wav_file:
                self.assertEqual(wav_file.getframerate(), 44100)
                self.assertEqual(wav_file.getnchannels(), 1)
                self.assertGreater(wav_file.getnframes(), 0)
            self.assertEqual(options["gain"], -12)

    def test_unknown_cue_is_ignored(self):
        class SceneStub:
            def add_sound(self, *_args, **_kwargs):
                raise AssertionError("unknown cues must not reach Manim")

        self.assertFalse(sound_design.add(SceneStub(), "unknown"))


if __name__ == "__main__":
    unittest.main()