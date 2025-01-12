import numpy as np
import mlx.core as mx
from ..inference_engine import InferenceEngine
from .sharded_model import StatefulShardedModel
from .sharded_utils import load_shard
from ..shard import Shard

class MLXFixedShardInferenceEngine(InferenceEngine):
    def __init__(self, model_path: str, shard: Shard):
        print("initializing fixed shard inference", shard)
        self.shard = shard
        model_shard, self.tokenizer = load_shard(model_path, shard)
        self.stateful_sharded_model = StatefulShardedModel(shard, model_shard)

    async def infer_prompt(self, shard: Shard, prompt: str) -> (np.ndarray, bool):
        if shard != self.shard:
            raise ValueError(f"Shard mismatch: {shard} != {self.shard}")

        output_data: np.ndarray = np.array(self.stateful_sharded_model.step(mx.array(self.tokenizer.encode(prompt))))
        print(f"output_data size: {output_data.size}, output_data: {output_data}")
        return output_data, output_data.size == 1 and output_data.item() == self.tokenizer.eos_token_id

    async def infer_tensor(self, shard: Shard, input_data: np.ndarray) -> (np.ndarray, bool):
        if shard != self.shard:
            raise ValueError(f"Shard mismatch: {shard} != {self.shard}")

        output_data: np.ndarray = np.array(self.stateful_sharded_model.step(mx.array(input_data)))
        return output_data, output_data.size == 1 and output_data.item() == self.tokenizer.eos_token_id

    async def reset_shard(self, shard: Shard):
        if shard != self.shard:
            raise ValueError(f"Shard mismatch: {shard} != {self.shard}")

        print(f"Resetting shard: {shard}")
        self.stateful_sharded_model.reset()

class MLXDynamicShardInferenceEngine(InferenceEngine):
    def __init__(self):
        self.shard = None

    async def infer_prompt(self, shard: Shard, prompt: str) -> (np.ndarray, bool):
        await self.ensure_shard(shard)
        output_data: np.ndarray = np.array(self.stateful_sharded_model.step(mx.array(self.tokenizer.encode(prompt))))
        return output_data, output_data.size == 1 and output_data.item() == self.tokenizer.eos_token_id

    async def infer_tensor(self, shard: Shard, input_data: np.ndarray) -> (np.ndarray, bool):
        await self.ensure_shard(shard)
        output_data: np.ndarray = np.array(self.stateful_sharded_model.step(mx.array(input_data)))
        return output_data, output_data.size == 1 and output_data.item() == self.tokenizer.eos_token_id

    async def reset_shard(self, shard: Shard):
        await self.ensure_shard(shard)

        print(f"Resetting shard: {shard}")
        self.stateful_sharded_model.reset()

    async def ensure_shard(self, shard: Shard):
        if self.shard == shard:
            return

        model_shard, self.tokenizer = load_shard(shard.model_id, shard)
        self.stateful_sharded_model = StatefulShardedModel(shard, model_shard)
        self.shard = shard
