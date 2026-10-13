import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from manim import Dot

import visual_kit


class FakeScene:
    def __init__(self):
        self.mobjects = []

    def play(self, *args, **kwargs):
        return None

    def wait(self, *args, **kwargs):
        return None


class VisualKitStoryCalloutTests(unittest.TestCase):
    def test_story_callout_works_for_target_and_hint(self):
        scene = FakeScene()
        target = Dot(point=[0, 0, 0])

        callout = visual_kit.story_callout(
            scene,
            target,
            "IDEA",
            subtitle="One idea at a time",
            detail="The key is to make the structure visible.",
        )

        self.assertIsNotNone(callout)
        self.assertGreater(len(callout), 0)


if __name__ == "__main__":
    unittest.main()
