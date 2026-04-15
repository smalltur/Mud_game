import os
import random
import re
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, SystemMessage

# API key is set in main.cpp via environment variable

llm = ChatOpenAI(
    openai_api_base="https://api.deepseek.com/v1",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY", "sk-0a69f5b6461d4a1788793a20103de3b5"),
    model="deepseek-chat",
    temperature=0.7,
    max_tokens=300,
)

# 读取状态
try:
    with open('npc_state.txt', 'r') as f:
        state = f.read().strip()
except FileNotFoundError:
    state = 'start'

with open('temp_input.txt', 'r') as f:
    user_input = f.read().strip()

# 根据状态生成prompt
if state == 'start':
    prompt = "你是一个古代中国的码头负责人，生活在水浒传时代，只负责给用户发布游戏任务和消息。你第一句话必须是问：要找活计还是打听消息？"
elif state == 'waiting_choice':
    prompt = f"用户输入: {user_input}。如果用户选择找活计，随机生成一个合适的任务（如运货、打扫码头等）和随机1-100盘缠，明确说明任务可以获得多少盘缠，并询问是否同意。把任务内容和奖励都写清楚，不要有多余内容。如果选择打听消息，随机生成一则江湖消息，并直接回复消息内容。如果用户回答其他内容，则礼貌推脱，将对话引回消息和活计上。"
elif state == 'waiting_agree':
    try:
        with open('task_info.txt', 'r') as f:
            task_info = f.read().strip()
            task, gold = task_info.split(':')
    except:
        task_info = "运货:50"
        task, gold = "运货", "50"
    prompt = f"用户输入: {user_input}。之前提出的任务: {task}，盘缠: {gold}。如果用户同意或确认完成，确认完成任务，添加盘缠，退出对话。必须输出EXIT: true和ACTION: add_gold:{gold}。如果不同意，礼貌拒绝并退出，输出EXIT: true和ACTION: none。如果用户回答其他内容，则礼貌推脱，并将对话引回消息和活计上。"
else:
    prompt = f"用户输入: {user_input}。结束对话。"

system_message = SystemMessage(content="你是一个古代中国的码头负责人，生活在水浒传时代，只负责给用户发布游戏任务和消息，与你任务无关的用户话题全部搪塞过去。用“盘缠”作为货币。请用中文回应。输出格式严格如下：RESPONSE: [你的回应文本] EXIT: [true或false] ACTION: [如果需要修改角色属性，如add_gold:50，否则none]")

messages = [system_message, HumanMessage(content=prompt)]
llm_response = llm.invoke(messages).content

# 解析LLM输出
response = ""
should_exit = False
action = ""

lines = llm_response.split('\n')
for line in lines:
    if line.startswith('RESPONSE:'):
        response = line[9:].strip()
    elif line.startswith('EXIT:'):
        exit_str = line[5:].strip().lower()
        should_exit = exit_str == 'true'
    elif line.startswith('ACTION:'):
        action = line[7:].strip()
        if action.lower() == 'none':
            action = ""

# 更新状态
if state == 'start':
    state = 'waiting_choice'
elif state == 'waiting_choice':
    if '活计' in user_input.lower() or '工作' in user_input.lower() or '找活' in user_input.lower():
        state = 'waiting_agree'
        match = re.search(r'(?:任务|活计|做).*?(?:赚|给).*?([0-9]+).*?盘缠', response)
        if match:
            gold = match.group(1)
            match_task = re.search(r'([\u4e00-\u9fa5]{2,10})(?:的活计|活计)', response)
            task = match_task.group(1) if match_task else '活计'
            with open('task_info.txt', 'w') as f:
                f.write(f"{task}:{gold}")
    else:
        state = 'done'
elif state == 'waiting_agree':
    state = 'done'
else:
    state = 'done'

if should_exit:
    state = 'done'

# 写状态
with open('npc_state.txt', 'w') as f:
    f.write(state)

# 写输出
output = response
if should_exit:
    output += "\nEXIT"
if action:
    output += f"\nACTION:{action}"

with open('temp_output.txt', 'w') as f:
    f.write(output)