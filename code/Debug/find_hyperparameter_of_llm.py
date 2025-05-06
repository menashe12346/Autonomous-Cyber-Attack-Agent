from models.llama_cpp import Llama

llm = Llama(model_path="path/to/model.gguf")
print(llm.parameters['n_ctx'])