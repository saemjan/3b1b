import csv
import importlib.util
import os
import tempfile
import unittest
import json


TEST_FILE = os.path.join(os.path.dirname(__file__), '..', 'tools', 'generate_topic_bundle.py')


spec = importlib.util.spec_from_file_location('generate_topic_bundle', TEST_FILE)
module = importlib.util.module_from_spec(spec)


class TopicBundleGeneratorTests(unittest.TestCase):
    def test_unmatched_topic_keeps_generic_storyboard(self):
        if spec is None or spec.loader is None:
            self.fail('generator module spec is unavailable')
        spec.loader.exec_module(module)
        row = module.build_row(
            'wave_speed_short', 'Wave Speed',
            'How are frequency, wavelength, and wave speed related?',
            'horizontal', 'short',
        )
        visuals = __import__('json').loads(row['visual_data_json'])
        self.assertFalse(any(item['type'] == 'falling_energy' for item in visuals))
        self.assertGreaterEqual(len(visuals), 9)
        self.assertEqual(row['correct_answer'], '')

    def test_energy_fall_uses_specialized_animated_visual(self):
        if spec is None or spec.loader is None:
            self.fail('generator module spec is unavailable')
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmpdir:
            rows = module.build_bundle(
                concept='Conservation of Energy',
                problem='A 2 kg object falls 5 m. What is the loss in potential energy?',
                output_path=os.path.join(tmpdir, 'energy.csv'),
                kind='both',
            )

        for row in rows:
            visuals = __import__('json').loads(row['visual_data_json'])
            energy_scene = next((item for item in visuals if item['type'] == 'falling_energy'), None)
            self.assertIsNotNone(energy_scene)
            self.assertEqual(energy_scene['id'], 'energy_model')
            self.assertTrue(any('mgh' in equation for equation in __import__('json').loads(row['equations_json'])))

    def test_generates_short_and_lecture_rows_for_any_concept(self):
        if spec is None or spec.loader is None:
            self.fail('generator module spec is unavailable')
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, 'bundle.csv')
            module.build_bundle(
                concept='Conservation of Energy',
                problem='A 2 kg object falls 5 m. What is the loss in potential energy?',
                output_path=out,
                kind='both',
            )

            with open(out, newline='', encoding='utf-8') as fh:
                rows = list(csv.DictReader(fh))

            self.assertEqual(len(rows), 2)
            self.assertEqual({row['orientation'] for row in rows}, {'horizontal', 'vertical'})
            self.assertTrue(any(row['video_id'].endswith('_short') for row in rows))
            self.assertTrue(any(row['video_id'].endswith('_lecture') for row in rows))
            by_id = {row['video_id']: row for row in rows}
            short = by_id['conservation_of_energy_short']
            lecture = by_id['conservation_of_energy_lecture']
            self.assertGreaterEqual(len(short['audio_script'].split()), 110)
            self.assertLessEqual(len(short['audio_script'].split()), 165)
            self.assertGreaterEqual(len(lecture['audio_script'].split()), 320)
            self.assertLessEqual(len(lecture['audio_script'].split()), 430)
            self.assertEqual(short['target_duration_sec'], '60')
            self.assertEqual(lecture['target_duration_sec'], '180')

            for row in rows:
                visuals = __import__('json').loads(row['visual_data_json'])
                beats = __import__('json').loads(row['beats_json'])
                visual_ids = {visual['id'] for visual in visuals}
                self.assertGreaterEqual(len(visuals), 3)
                self.assertTrue(all(beat['focus'] in visual_ids for beat in beats))
                prompt = next(item for item in visuals if item['id'] == 'question_prompt')
                self.assertIn('2 kg object falls 5 m', prompt['text'])
                self.assertEqual(row['option_a'], '')
                self.assertIn('98.1 J', row['correct_answer'])

    def test_feynman_series_contains_ten_paired_original_topics(self):
        series_path = os.path.join(
            os.path.dirname(__file__), '..', 'tools',
            'generate_feynman_series.py',
        )
        series_spec = importlib.util.spec_from_file_location(
            'generate_feynman_series', series_path,
        )
        series = importlib.util.module_from_spec(series_spec)
        series_spec.loader.exec_module(series)

        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, 'series.csv')
            rows = series.write_batch(output)

            with open(output, newline='', encoding='utf-8') as fh:
                parsed = list(csv.DictReader(fh))

        self.assertEqual(len(rows), 20)
        self.assertEqual(len(parsed), 20)
        self.assertEqual(
            {orientation: sum(row['orientation'] == orientation
                              for row in parsed)
             for orientation in ('horizontal', 'vertical')},
            {'horizontal': 10, 'vertical': 10},
        )
        self.assertEqual(
            {duration: sum(row['target_duration_sec'] == duration
                           for row in parsed)
             for duration in ('60', '180')},
            {'60': 10, '180': 10},
        )
        for row in parsed:
            words = len(row['audio_script'].split())
            if row['orientation'] == 'horizontal':
                self.assertGreaterEqual(words, 112)
                self.assertLessEqual(words, 180)
            else:
                self.assertGreaterEqual(words, 337)
                self.assertLessEqual(words, 540)
            visuals = json.loads(row['visual_data_json'])
            beats = json.loads(row['beats_json'])
            visual_ids = {visual['id'] for visual in visuals}
            self.assertTrue(all(beat['focus'] in visual_ids for beat in beats))


if __name__ == '__main__':
    unittest.main()
