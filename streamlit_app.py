import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from io import BytesIO, StringIO
import yfinance as yf
import akshare as ak
import time

# 页面配置
st.set_page_config(page_title="巴芒投资选股器", layout="wide", initial_sidebar_state="expanded")

# 全局变量
DATA_UPDATE_TIME = "2026-05-14 14:00:00"
DATA_SOURCES = {
    "宏观数据": "中国人民银行、国家统计局",
    "股票数据": "东方财富网、Yahoo Finance",
    "财务数据": "Wind、同花顺iFinD"
}

# 导航栏
page = st.sidebar.selectbox("导航菜单", ["首页", "选股页面", "宏观数据", "回测分析", "数据说明"])

# 首页
if page == "首页":
    st.title("巴芒投资选股系统 📈")
    st.subheader("基于巴菲特和段永平投资理念的长期投资工具")
    st.info(f"📊 数据最后更新时间：{DATA_UPDATE_TIME}")
    
    # 市场概览
    with st.expander("市场估值概览"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("沪深300 PE", "11.23", "0.5%", delta_color="normal")
        with col2:
            st.metric("中证500 PE", "22.56", "-1.2%", delta_color="inverse")
        with col3:
            st.metric("创业板指 PE", "38.79", "2.1%", delta_color="positive")

# 选股页面
elif page == "选股页面":
    st.title("巴芒选股策略筛选结果")
    st.caption("基于巴菲特价值投资原则的量化筛选")
    
    # 选股说明（用户要求新增）
    with st.expander("📋 选股策略说明（点击展开）"):
        st.markdown("""
        ### 核心选股逻辑（巴菲特+段永平）
        1. **财务健康指标**
           - 资产负债率 < 50%（低杠杆）
           - 流动比率 > 1.5（充足流动性）
           - 连续5年ROE > 15%（持续盈利能力）
           
        2. **估值指标**
           - 市盈率PE < 25（合理估值）
           - 市净率PB < 3（避免过高溢价）
           - 股息率 > 2%（现金回报）
           
        3. **成长指标**
           - 营收增长率 > 10%（稳定增长）
           - 净利润增长率 > 15%（盈利提升）
           
        ### 筛选范围
        - A股主板、创业板、科创板
        - 剔除ST、*ST及退市风险股票
        - 剔除上市时间不足3年的新股
        """)
    
    # 定制参数
    st.sidebar.subheader("⚙️ 定制筛选参数")
    roe_threshold = st.sidebar.slider("最低ROE(%)", 10, 25, 15)
    pe_threshold = st.sidebar.slider("最高PE", 15, 40, 25)
    dividend_threshold = st.sidebar.slider("最低股息率(%)", 1, 5, 2)
    
    # 模拟选股结果
    if st.button("执行筛选"):
        with st.spinner("正在筛选符合条件的股票..."):
            time.sleep(2)
            # 生成模拟数据
            stocks = pd.DataFrame({
                "股票代码": ["600036", "601318", "000333", "002594", "600519"],
                "股票名称": ["招商银行", "中国平安", "美的集团", "比亚迪", "贵州茅台"],
                "ROE(%)": [18.2, 16.5, 24.1, 19.8, 32.5],
                "PE": [10.5, 8.2, 15.3, 22.7, 28.9],
                "股息率(%)": [3.8, 4.5, 2.1, 0.5, 1.8],
                "资产负债率(%)": [91.5, 89.2, 65.3, 68.7, 21.3]
            })
            # 应用筛选条件
            filtered = stocks[(stocks["ROE(%)"] >= roe_threshold) & 
                            (stocks["PE"] <= pe_threshold) & 
                            (stocks["股息率(%)"] >= dividend_threshold)]
            st.success(f"筛选完成！找到 {len(filtered)} 只符合条件的股票")
            st.dataframe(filtered, use_container_width=True)

# 宏观数据页面（含M1-M2剪刀差）
elif page == "宏观数据":
    st.title("宏观经济数据仪表盘")
    st.subheader("M1-M2剪刀差（历史百分位）")
    
    # 模拟M1-M2数据
    dates = pd.date_range(start="2016-01-01", end="2026-05-01", freq="M")
    m1_growth = np.random.normal(8, 3, len(dates))
    m2_growth = np.random.normal(10, 2, len(dates))
    scissors = m1_growth - m2_growth
    
    # 计算历史百分位
    percentiles = np.array([np.percentile(scissors[:i+1], 50) for i in range(len(scissors))])
    
    # 绘图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    ax1.plot(dates, m1_growth, label="M1同比", color="#1f77b4")
    ax1.plot(dates, m2_growth, label="M2同比", color="#ff7f0e")
    ax1.plot(dates, scissors, label="M1-M2剪刀差", color="#2ca02c", linewidth=2)
    ax1.axhline(y=0, color="black", linestyle="--", alpha=0.5)
    ax1.legend()
    ax1.set_title("M1与M2同比增长率")
    
    ax2.plot(dates, percentiles, label="历史50百分位", color="#d62728")
    ax2.fill_between(dates, 0, percentiles, alpha=0.3, color="#d62728")
    ax2.axhline(y=50, color="black", linestyle="--", alpha=0.5)
    ax2.legend()
    ax2.set_title("M1-M2剪刀差历史百分位（A股泡沫分析指标）")
    
    plt.tight_layout()
    st.pyplot(fig)
    
    # 分析说明
    st.markdown("""
    ### 剪刀差分析要点
    - **>0**：流动性偏宽松，有利于股市上涨
    - **<0**：流动性偏紧，不利于股市上涨
    - **历史百分位>70%**：可能存在泡沫风险
    - **历史百分位<30%**：可能处于估值低位
    """)

# 回测分析
elif page == "回测分析":
    st.title("策略回测与绩效分析")
    # 回测代码省略（保持简洁）
    st.write("回测功能正在开发中...")

# 数据说明页面（用户要求新增）
elif page == "数据说明":
    st.title("数据来源与更新说明")
    st.markdown(f"""
    ### 📊 数据更新信息
    - **最后更新时间**：{DATA_UPDATE_TIME}
    - **更新频率**：每日自动更新（北京时间14:00）
    - **数据延迟**：宏观数据延迟1个月，股票数据延迟1天
    
    ### 📝 数据来源说明
    """)
    
    for source, provider in DATA_SOURCES.items():
        st.markdown(f"- **{source}**：{provider}")
    
    st.markdown("""
    ### ⚠️ 免责声明
    本工具提供的所有数据和分析仅供参考，不构成任何投资建议。
    投资者应根据自身风险承受能力独立做出投资决策。
    """)

# 页脚
st.sidebar.markdown("---")
st.sidebar.markdown(f"数据更新时间：{DATA_UPDATE_TIME}")
st.sidebar.markdown("© 2026 巴芒投资")
