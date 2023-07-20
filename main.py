import openai
import streamlit as st
import tiktoken

openai.api_key = st.secrets['chatanywhere']['api_key']
openai.api_base = "https://api.chatanywhere.cn/v1"  # 使用从chatanywhere购买的便宜key


st.set_page_config(page_title='天同学的GPT', page_icon=None, layout="centered", initial_sidebar_state="auto", menu_items=None)

if "messages" not in st.session_state:
    st.session_state["messages"] = [{'role': 'system', 'content': ''}]
    st.session_state["use_num_all1"] = st.session_state["use_num_all2"] = st.session_state['money'] = 0
    
with st.sidebar:
    st.markdown('## 模型切换')
    model = st.selectbox('模型切换', ['gpt-3.5-turbo', 'gpt-4'], label_visibility='collapsed')
    st.divider()
#------------------------------    
def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens
#------------------------------ 


#------------------------------系统提示词
with st.expander('系统提示词'):
    system = st.text_area('系统提示词', height=300, label_visibility='collapsed')
    st.session_state["messages"][0]['content'] = system  

#------------------------------

for msg in st.session_state.messages[1:]:
    st.chat_message(msg["role"], avatar=msg.get('avatar')).write(msg["content"])

use_num1 = use_num2 = money = 0


#------------------------------处理提交逻辑
if prompt := st.chat_input():
    prompt = prompt.replace('\n', '\n\n')
    st.session_state['messages'].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    use_num1 = num_tokens_from_messages(st.session_state['messages'], model)
    st.session_state["use_num_all1"] += use_num1
    with st.chat_message('assistant'):
        with st.empty():
            msg = ''
            rep = openai.ChatCompletion.create(
                model=model, 
                messages=st.session_state.messages, 
                stream=True,
                temperature=1,
            )
            for r in rep:
                msg += r['choices'][0]['delta'].get('content', '')
                st.write(msg)
    use_num2 = len(tiktoken.encoding_for_model(model).encode(msg))
    st.session_state["use_num_all2"] += use_num2
    st.session_state['messages'].append({"role": "assistant", "content": msg})
    if model == 'gpt-4':
        p1, p2 = 0.03, 0.06
    else:
        p1, p2 = 0.0015, 0.002
    money = (use_num1 * p1 + use_num2 * p2) / 1000 * 7
    st.session_state['money'] += money
    
    # st.write(len(st.session_state["messages"]))
#------------------------------





#---------------------------------------侧边栏
with st.sidebar:
    with st.expander('清除聊天记录'):
        def remake():
            del st.session_state['messages'][1:] 
        def remake_one():
            if len(st.session_state['messages']) > 1:
                del st.session_state['messages'][-1]
        col1, col2 = st.columns(2)
        with col1:
            st.button("删除全部", on_click=remake)
        with col2:
            st.button("删除一条", on_click=remake_one)
    
    with st.expander('token和费用'):
        always_show = st.checkbox('问答下方即时显示花费', )  # value=True
        col1, col2, col3 = st.columns(3)
        col1.metric('prompt', st.session_state["use_num_all1"], delta=use_num1)
        col2.metric('completion', st.session_state["use_num_all2"], delta=use_num2)
        col3.metric('total', st.session_state["use_num_all1"] + st.session_state["use_num_all2"], delta=use_num1+use_num2)
        m = st.session_state['money']
        st.metric('共计花费（人民币）', f'{m:.2f} 元', delta=f'{money:.4f}')


if always_show and use_num1:
    st.write(f'本次提交花费 ', use_num1, ' 个prompt token, ', use_num2, ' 个completion token ', '共计 ',use_num1 + use_num2, ' 个token, 折算人民币 ', round(money, 4))
