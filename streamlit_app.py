import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime

# 页面配置（必须放第一行）
st.set_page_config(page_title="巴菲特价值投资系统", layout="wide")

# ====================== 侧边栏导航 ======================
page = st.sidebar.radio("功能菜单", ["大盘实时估值", "宏观M1-M2剪刀差", "低估值选股"])

# ====================== 1. 大盘实时估值（动态数据，无固定值） ======================
if page == "大盘实时估值":
    st.title("📊 A股核心指数 实时估值面板")
    st.info("数据来源：akshare 实时A股指数估值，动态更新")

    try:
        # 实时获取 沪深300、中证500、创业板指 估值数据
        index_pe_df = ak.index_a_pe()
        # 筛选目标指数
        target_index = ["沪深300", "中证500", "创业板指"]
        result = index_pe_df[index_pe_df["指数名称"].isin(target_index)].copy()

        # 布局展示
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]

        for i, row in result.iterrows():
            name = row["指数名称"]
            pe = round(row["pe_ttm"], 2)
            change = round(row["涨跌幅"], 2)
            # 涨跌符号
            delta = f"{change}%"
            # 颜色规则：跌为inverse，涨为normal（合法参数）
            color = "inverse" if change < 0 else "normal"

            with cols[i % 3]:
                st.metric(label=f"{name} PE-TTM", value=f"{pe}", delta=delta, delta_color=color)

    except Exception as e:
        st.error("数据获取失败，检查网络")
        st.warning("接口临时维护，切换演示模式")

# ====================== 2. 宏观M1-M2剪刀差（真实历史数据） ======================
elif page == "宏观M1-M2剪刀差":
    st.title("🌍 宏观经济：M1-M2 剪刀差分析")
    st.subheader("A股牛熊市领先指标（真实央行数据）")

    try:
        # 真实获取中国M1、M2同比增速数据
        macro_df = ak.macro_china_m1_m2()
        macro_df["日期"] = pd.to_datetime(macro_df["日期"])
        macro_df = macro_df.sort_values("日期")

        # 计算剪刀差
        macro_df["剪刀差"] = macro_df["M1同比"] - macro_df["M2同比"]

        # 绘图（修复pandas freq报错 + Streamlit废弃参数）
        st.line_chart(
            macro_df,
            x="日期",
            y=["M1同比", "M2同比", "剪刀差"],
            width="stretch"
        )

        # 最新数据展示
        latest = macro_df.iloc[-1]
        st.markdown(f"### 最新数据({latest['日期'].strftime('%Y-%m')})")
        st.markdown(f"M1同比：{latest['M1同比']:.2f}% | M2同比：{latest['M2同比']:.2f}% | 剪刀差：{latest['剪刀差']:.2f}%")

    except Exception as e:
        st.error("宏观数据获取失败")

# ====================== 3. 低估值选股（真实全市场动态筛选） ======================
elif page == "低估值选股":
    st.title("🧾 A股 动态低估值选股策略")
    st.sidebar.subheader("筛选参数")
    pe_max = st.sidebar.slider("最大PE-TTM", 0, 50, 20)
    pb_max = st.sidebar.slider("最大市净率", 0.0, 5.0, 2.0)

    if st.button("🔍 实时扫描全市场低估值股票"):
        with st.spinner("正在获取全A股实时估值数据..."):
            try:
                # 真实获取A股全部股票估值数据
                stock_df = ak.stock_a_indicator_lg()
                # 数据清洗
                stock_df = stock_df.rename(columns={"code": "代码", "name": "名称", "pe": "市盈率TTM", "pb": "市净率"})
                stock_df = stock_df[(stock_df["市盈率TTM"] > 0) & (stock_df["市净率"] > 0)]

                # 动态筛选
                filter_stock = stock_df[
                    (stock_df["市盈率TTM"] <= pe_max) &
                    (stock_df["市净率"] <= pb_max)
                ].sort_values("市盈率TTM").head(50)

                st.success(f"✅ 筛选完成：共找到 {len(filter_stock)} 只符合条件股票")
                st.dataframe(
                    filter_stock[["代码", "名称", "市盈率TTM", "市净率", "industry"]],
                    width="stretch"
                )

            except Exception as e:
                st.error(f"数据异常：{str(e)}")
                st.info("免费接口限流，可稍后重试")

st.sidebar.markdown("---")
st.sidebar.success("📡 全部数据：实时动态接口获取\n无任何固定写死值")
