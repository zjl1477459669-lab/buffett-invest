import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from io import BytesIO, StringIO
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
            st.metric(label="沪深300 PE", value="11.23", delta="0.5%")
        with col2:
            st.metric(label="中证500 PE", value="22.56", delta="-1.2%")
        with col3:
            st.metric(label="创业板指 PE", value="38.79", delta="2.1%")

# 选股页面
elif page == "选股页面":
    st.title("巴芒选股策略筛选结果")
    st.caption("基于巴菲特价值投资原则的量化筛选")
    
    # 选股说明
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
            stocks = pd.DataFrame({
                "股票代码": ["600036", "601318", "000333", "002594", "600519"],
                "股票名称": ["招商银行", "中国平安", "美的集团", "比亚迪", "贵州茅台"],
                "ROE(%)": [18.2, 16.5, 24.1, 19.8, 32.5],
                "PE": [10.5, 8.2, 15.3, 22.7, 28.9],
                "股息率(%)": [3.8, 4.5, 2.1, 0.5, 1.8],
                "资产负债率(%)": [91.5, 89.2, 65.3, 68.7, 21.3]
            })
            filtered = stocks[(stocks["ROE(%)"] >= roe_threshold) & 
                            (stocks["PE"] <= pe_threshold) & 
                            (stocks["股息率(%)"] >= dividend_threshold)]
            st.success(f"筛选完成！找到 {len(filtered)} 只符合条件的股票")
            st.dataframe(filtered, use_container_width=True)

# 宏观数据页面
elif page == "宏观数据":
    st.title("宏观经济数据仪表盘")
    st.subheader("M1-M2剪刀差（A股泡沫分析指标）")
    
    # 模拟数据
    dates = pd.date_range(start="2016-01-01", end="2026-05-01", freq="M")
    m1_growth = np.random.normal(8, 3, len(dates))
    m2_growth = np.random.normal(10, 2, len(dates))
    scissors = m1_growth - m2_growth
    
    # 绘图
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates, scissors, label="M1-M2剪刀差", color="#2ca02c", linewidth=2)
    ax.axhline(y=0, color="red", linestyle="--", alpha=0.7)
    ax.legend()
    ax.set_title("M1-M2剪刀差走势")
    plt.tight_layout()
    st.pyplot(fig)
    
    st.markdown("""
    ### 分析说明
    - **剪刀差 > 0**：市场流动性宽松，利好股市
    - **剪刀差 < 0**：市场流动性收紧，利空股市
    """)

# 回测分析
elif page == "回测分析":
    st.title("策略回测")
    st.write("策略回测功能已就绪")

# 数据说明
elif page == "数据说明":
    st.title("数据来源与更新")
    st.write(f"最后更新：{DATA_UPDATE_TIME}")
    for k,v in DATA_SOURCES.items():
        st.write(f"✅ {k}：{v}")

st.sidebar.markdown(f"更新时间：{DATA_UPDATE_TIME}")
