# src/report_builder.py
class ReportBuilder:

    @staticmethod
    def build(profile, brooks_result):
        decision = "观望"
        if brooks_result["type"] == "BUY":
            decision = "买入"
        elif brooks_result["type"] == "SELL":
            decision = "卖出"

        return f"""
🎯 {profile['code']}（{profile['name']}）

📌 市场判断：{decision}
📐 价格行为：{brooks_result['reason']}

一句话：
这是一个基于 Al Brooks 价格行为的判断结果。
"""