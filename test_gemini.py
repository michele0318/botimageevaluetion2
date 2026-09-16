"""No network, keys, browser or submissions: exercise billing and refusal paths."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import requests
import run_task_bot as bot
import gemini_provider as gemini


class GeminiTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.state = patch.object(bot, 'STATE', Path(self.directory.name))
        self.state.start()
        self.settings = patch.object(gemini, 'config', return_value={'provider': 'gemini', 'model': gemini.DEFAULT_MODEL, 'daily_usd': 1})
        self.settings.start()
        self.secret = patch.object(gemini, 'key', return_value='test-secret')
        self.secret.start()
        self.prices = patch.object(gemini, 'rates', return_value=(.75, 3.75))
        self.prices.start()
        buf = io.BytesIO()
        Image.new('RGB', (16, 16)).save(buf, 'PNG')
        self.picture = buf.getvalue()

    def tearDown(self):
        self.prices.stop()
        self.secret.stop()
        self.settings.stop()
        self.state.stop()
        self.directory.cleanup()

    def response(self, answer='{"choice":"2"}', finish='STOP'):
        return {'candidates': [{'finishReason': finish, 'content': {'parts': [{'text': answer}]}}],
                'usageMetadata': {'promptTokenCount': 1000, 'totalTokenCount': 1500,
                                  'candidatesTokenCount': 20, 'thoughtsTokenCount': 480}}

    def test_images_prompt_and_thinking_cost(self):
        metrics = {}
        with patch.object(gemini, 'post', side_effect=[{'totalTokens': 1000}, self.response()]) as post:
            result = gemini.generate('rules', 'entire prompt', [self.picture, self.picture],
                                     [{'label': 'style', 'data': self.picture}], metrics, choice=True)
        self.assertEqual(result, '2')
        request = post.call_args_list[1].args[2]
        parts = request['contents'][0]['parts']
        self.assertEqual([p['text'] for p in parts if 'text' in p],
                         ['entire prompt', 'CANDIDATE 1', 'CANDIDATE 2', 'REFERENCE R1 (not a candidate): style'])
        self.assertEqual(sum('inlineData' in p for p in parts), 3)
        self.assertAlmostEqual(metrics['estimated_usd'], .002625)

    def test_budget_blocks_generation(self):
        gemini.reserve(1, 1)
        with patch.object(gemini, 'post', return_value={'totalTokens': 1000}) as post:
            with self.assertRaises(bot.Stop):
                gemini.generate('rules', 'prompt', choice=True)
        self.assertEqual(post.call_count, 1)

    def test_timeout_reservation_remains(self):
        with patch.object(gemini, 'post', side_effect=[{'totalTokens': 1000}, bot.Stop('timeout')]):
            with self.assertRaises(bot.Stop):
                gemini.generate('rules', 'prompt', choice=True)
        with gemini.ledger() as db:
            amount, status = db.execute('SELECT usd,status FROM calls').fetchone()
        self.assertGreater(amount, 0)
        self.assertEqual(status, 'reserved')

    def test_no_answer_on_invalid_or_truncated_output(self):
        for answer, finish in [('not json', 'STOP'), ('{"choice":"3"}', 'STOP'), ('{"choice":"1"}', 'MAX_TOKENS')]:
            with patch.object(gemini, 'post', side_effect=[{'totalTokens': 1000}, self.response(answer, finish)]):
                with self.assertRaises(bot.Stop):
                    gemini.generate('rules', 'prompt', choice=True)

    def test_transport_does_not_retry_or_expose_key(self):
        with patch.object(gemini.HTTP, 'post', side_effect=requests.Timeout('secret')) as post:
            with self.assertRaises(bot.Stop) as error:
                gemini.post(gemini.DEFAULT_MODEL, 'generateContent', {}, 'test-secret')
        self.assertEqual(post.call_count, 1)
        self.assertNotIn('test-secret', str(error.exception))
        self.assertNotIn('test-secret', post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs['headers']['x-goog-api-key'], 'test-secret')

    def test_cloud_does_not_load_ollama(self):
        with patch.object(bot.LOCAL_HTTP, 'post') as post:
            bot.ollama_check()
            bot.warmup()
        post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
