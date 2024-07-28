import json
import os

import pandas as pd
from collections import deque

csv_folder = './data/csv'
print(f'当前处理目录{csv_folder}')


def handle_pt_csv(csvfile):
    chat_df = pd.read_csv(csvfile)
    chat_df = chat_df[chat_df['IsSender'] == 1]
    # 对每一行的StrContent进行处理 转为dict 再取'msg'字段
    chat_df['StrContent'] = chat_df['StrContent'].apply(lambda x: json.loads(x)['msg'])
    # 如果StrContent 包含 手机号、身份证号、邮箱、网址则删除这行
    chat_df = chat_df[~chat_df['StrContent'].str.contains('1\d{10}')]
    chat_df = chat_df[~chat_df['StrContent'].str.contains('\d{18}')]
    chat_df = chat_df[~chat_df['StrContent'].str.contains('\w+@\w+')]
    chat_df = chat_df[~chat_df['StrContent'].str.contains('http')]
    chat_df = chat_df[~chat_df['StrContent'].str.contains(r'\\xa0')]
    chat_df = chat_df[~chat_df['StrContent'].str.contains(r'\\u')]

    # 纯StrContent
    chat_df = chat_df['StrContent']
    chat_df = chat_df.dropna()

    return chat_df


def make_pt_dataset():
    csv_res = []
    # csv文件夹里全是不同聊天对象文件夹 每个文件夹里是csv文件 先遍历不同聊天对象文件夹 再遍历聊天对象的csv文件
    for chat_obj_folder in os.listdir(csv_folder):
        chat_obj_folder_path = os.path.join(csv_folder, chat_obj_folder)
        for csvfile in os.listdir(chat_obj_folder_path):
            csvfile_path = os.path.join(chat_obj_folder_path, csvfile)
            chat_df = handle_pt_csv(csvfile_path)
            csv_res.append(chat_df)

    csv_res = pd.concat(csv_res)
    csv_res = csv_res.apply(lambda x: {'c': x})  # 设置数据集prompt键为c

    csv_res.to_json('./data/res_csv/pt-my.json', orient='records', force_ascii=False)


def handle_sft_csv(csvfile):
    chat_df = pd.read_csv(csvfile)
    chat_df = chat_df[chat_df['Type'] == 1]
    print(chat_df)

    chat_df = chat_df[['IsSender', 'StrContent', 'StrTime']]
    chat_df = chat_df.dropna()

    # 时间格式 2021-07-07 10:27:23
    # 遍历行 相同IsSender的行合并StrContent（）遇到不同IsSender就重新开始
    # StrTime字段保留最后的StrTime
    chat_df['StrTime'] = pd.to_datetime(chat_df['StrTime'])
    res_df = []
    last_IsSender = chat_df.iloc[0]['IsSender']
    last_StrContent: str = chat_df.iloc[0]['StrContent']
    last_StrTime = chat_df.iloc[0]['StrTime']
    # 超时处理 半天没说话就重新开始
    # 注意这里只是处理了组装成一个句子 最后封装对话、配对在make_sft_dataset
    # 遇到图片 连接 直接封装成一个句子
    for i, row in chat_df.iterrows():
        if last_StrContent == '':  # 重新开始
            last_StrContent = row['StrContent']
            last_IsSender = row['IsSender']
            last_StrTime = row['StrTime']
            continue
        if row['IsSender'] == last_IsSender:
            if row['StrTime'] - last_StrTime > pd.Timedelta(value='1h'):
                # 如果超时 前面的添加到res_df 并重新开始
                if last_StrContent[-1] == '，':
                    last_StrContent = last_StrContent[:-1] + '。'
                elif last_StrContent[-1] not in ['。', '！', '？', '…', '.']:
                    last_StrContent += '。'
                res_df.append({'IsSender': last_IsSender, 'StrContent': last_StrContent, 'StrTime': last_StrTime})
                last_StrContent = row['StrContent']
                last_StrTime = row['StrTime']
                continue
            # 如果StrContent的结尾没有标点符号则添加逗号，最后结尾是句号
            if last_StrContent[-1] not in ['。', '！', '？', '…', '，']:
                last_StrContent += '，'
            last_StrContent = last_StrContent + row['StrContent']
            last_StrTime = row['StrTime']
        else:
            if last_StrContent[-1] == '，':
                last_StrContent = last_StrContent[:-1] + '。'
            elif last_StrContent[-1] not in ['。', '！', '？', '…', '.']:
                last_StrContent += '。'
            res_df.append({'IsSender': last_IsSender, 'StrContent': last_StrContent, 'StrTime': last_StrTime})
            last_IsSender = row['IsSender']
            last_StrContent = row['StrContent']
            last_StrTime = row['StrTime']
    res_df = pd.DataFrame(res_df)
    return res_df


def make_sft_dataset():

    #     [
    #   {
    #     "instruction": "用户指令（必填）",
    #     "input": "用户输入（选填）",
    #     "output": "模型回答（必填）",
    #     "system": "系统提示词（选填）",
    #     "history": [
    #       ["第一轮指令（选填）", "第一轮回答（选填）"],
    #       ["第二轮指令（选填）", "第二轮回答（选填）"]
    #     ]
    #   }
    # ]

    csv_concat = []
    csv_res = []
    # csv文件夹里全是不同聊天对象文件夹 每个文件夹里是csv文件 先遍历不同聊天对象文件夹 再遍历聊天对象的csv文件
    for chat_obj_folder in os.listdir(csv_folder):
        chat_obj_folder_path = os.path.join(csv_folder, chat_obj_folder)
        for csvfile in os.listdir(chat_obj_folder_path):
            csvfile_path = os.path.join(chat_obj_folder_path, csvfile)
            chat_df = handle_sft_csv(csvfile_path)
            csv_concat.append(chat_df)

    csv_concat = pd.concat(csv_concat)
    print(csv_concat)
    # csv_res里IsSender必须是01 01 01 的顺序 csv_concat里不一定是01 01
    # 相差超过1小时的时间戳分为不同的对话
    # temp_res为一个长度为2的队列
    sender = deque(maxlen=100)
    receiver = deque(maxlen=100)
    last_StrTime = csv_concat.iloc[0]['StrTime']
    # 6种情况
    # temp_res 为空  遇到 0入队 遇到1不处理 遇到cut不处理
    # temp_res 有0  遇到0清空队列再入队 遇到1相差超过1小时清空队列 没有相差一小时入队再全部出队 遇到cut清空队列

    for i, row in csv_concat.iterrows():
        if len(receiver) == 0:
            if row['StrTime'] - last_StrTime > pd.Timedelta('1h'):
                sender.clear()
                last_StrTime = row['StrTime']
            elif row['IsSender'] == 1:
                sender.append(row['StrContent'])
                last_StrTime = row['StrTime']
            else:
                if len(sender) > 0:
                    receiver.append(row['StrContent'])
                last_StrTime = row['StrTime']
        else:
            if row['StrTime'] - last_StrTime > pd.Timedelta('1h') or row['IsSender'] == 1:
                csv_res.append({"instruction": ' '.join(sender), "output": ' '.join(receiver)})
                sender.clear()
                receiver.clear()
                if row['IsSender'] == 1:
                    sender.append(row['StrContent'])
                last_StrTime = row['StrTime']
            else:
                if len(sender) > 0:
                    receiver.append(row['StrContent'])
                last_StrTime = row['StrTime']


    csv_res_df = pd.DataFrame(csv_res)
    print(f'处理后数据量：{csv_res_df.shape[0]}')
    csv_res_df.to_json('./data/res_csv/sft/sft-my.json', orient='records', force_ascii=False)


if __name__ == '__main__':
    # make_pt_dataset()
    make_sft_dataset()
