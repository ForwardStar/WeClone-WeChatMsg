# WeClone-WeChatMsg

This repository is forked from https://github.com/xming521/WeClone. The only difference is that this repository could handle datasets extracted from [WeChatMsg](https://github.com/LC044/WeChatMsg/tree/master), and optimizes the data preprocessing.

To tune the LLM model with your chat history, firstly download [MemoTrace](https://memotrace.cn/). Log in to WeChat PC and migrate your WeChat data to it. Then export your chat histories to CSV files. Then follow the same procedure as instructed in WeClone repository.

Please note that this repository is only for personal use. Do not copy or share.

# Steps to run
1. Export your chat history to a .csv file through [MemoTrace](https://memotrace.cn/);
2. Create a directory "data/csv/chat" and place the exported .csv file to the directory;
3. Install the required python packages by ``pip install -r requirements``;
4. Run ``python make_dataset/csv_to_json.py`` to convert the dataset to a json file;
5. Run ``python src/train_sft.py`` to train the model;
6. Run ``python src/web_demo.py`` to launch the chatbot.