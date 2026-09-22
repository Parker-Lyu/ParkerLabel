import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np

from parker_label_app.inference import SegmentationEngine


class SegmentationEngineTests(unittest.TestCase):
    def test_reuses_only_the_selected_low_resolution_mask(self):
        engine = SegmentationEngine(Path("encoder.onnx"), Path("decoder.onnx"))
        engine.decoder_session = Mock()
        masks = np.zeros((1, 4, 2, 2), dtype=np.float32)
        masks[0, 2] = 1
        scores = np.array([[0.99, 0.4, 0.8, 0.2]], dtype=np.float32)
        logits = np.stack(
            [np.full((256, 256), index, dtype=np.float32) for index in range(4)]
        )[None]
        engine.decoder_session.run.return_value = (masks, scores, logits)
        embedding = np.zeros((1, 256, 64, 64), dtype=np.float32)

        mask, selected_logits, _ = engine.predict(
            embedding, (2, 2), [(1, 1)], [1]
        )
        _, second_logits, _ = engine.predict(
            embedding,
            (2, 2),
            [(1, 1), (0, 0)],
            [1, 0],
            selected_logits,
        )

        np.testing.assert_array_equal(mask, np.ones((2, 2), dtype=np.uint8))
        self.assertEqual(selected_logits.shape, (1, 1, 256, 256))
        np.testing.assert_array_equal(selected_logits, logits[:, 2:3])
        second_inputs = engine.decoder_session.run.call_args_list[1].args[1]
        self.assertEqual(second_inputs["mask_input"].shape, (1, 1, 256, 256))
        np.testing.assert_array_equal(second_inputs["mask_input"], selected_logits)
        np.testing.assert_array_equal(second_logits, logits[:, 0:1])


if __name__ == "__main__":
    unittest.main()
