_base_ = ['configs/agents/internvl/internvl2-2b.py']

from lmdeploy import ChatTemplateConfig

lmm_agent = dict(
    name='internvl3_5-8b',
    model='OpenGVLab/InternVL3_5-8B',
    chat_template=ChatTemplateConfig('internvl3'),  # if needed
)