# _base_ = ['configs/agents/internvl/internvl2-2b.py']

# from lmdeploy import ChatTemplateConfig

# lmm_agent = dict(
#     name='internvl3_5-8b',
#     model='OpenGVLab/InternVL3_5-8B',
#     chat_template=ChatTemplateConfig('internvl3'),  # if needed
# )



from lmdeploy import (ChatTemplateConfig, GenerationConfig,
                      TurbomindEngineConfig)

lmm_agent = dict(
    name='internvl3_5-8b',
    agent='lmdeploy_single',
    chat_template=ChatTemplateConfig('internvl3'),
    model='OpenGVLab/InternVL3_5-8B',
    backend_config=TurbomindEngineConfig(session_len=32768),  # ← Increased from 8192
    general_config=GenerationConfig(max_new_tokens=1024, top_p=0.8),
)