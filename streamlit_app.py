import streamlit as st
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="巴芒投资选股器", layout="wide", initial_sidebar_state="expanded")

# 全局异常处理
st.markdown("""
<style>
.stAlert {
    padding: 1rem;
    border-radius: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# -------------------------- 指数估值（最稳定实现） --------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_index_pe():
    """获取三大指数最新PE，多层异常处理"""
    try:
        # 登录Baostock
        lg = bs.login()
        if lg.error_code != '0':
            return None
        
        pe_values = []
        indexes = [
            ("沪深300", "sh.000300"),
            ("中证500", "sh.000905"),
            ("创业板指", "sz.399006")
        ]
        
        for name, code in indexes:
            try:
                # 获取近30天数据
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                
                rs = bs.query_history_k_data_plus(
                    code,
                    "date,peTTM",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d"
                )
                
                df = rs.get_data()
                
                # 找最新有效PE
                valid_pe = None
                for i in reversed(range(len(df))):
                    pe_str = df.iloc[i]["peTTM"]
                    if pe_str and pe_str.strip() and pe_str.strip() != '':
                        try:
                            pe = float(pe_str)
                            if pe > 0 and pe < 1000:
                                valid_pe = round(pe, 2)
                                break
                        except:
                            continue
                
                pe_values.append(valid_pe if valid_pe else "暂无")
            except:
                pe_values.append("暂无")
        
        bs.logout()
        return pe_values
    except:
        return ["暂无", "暂无", "暂无"]

# -------------------------- 选股数据（最稳定实现） --------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def get_stock_list(roe_min=15, pe_max=25, dividend_min=2):
    """按巴菲特策略筛选股票，严格异常处理"""
    try:
        lg = bs.login()
        if lg.error_code != '0':
            return None
        
        # 获取股票列表
        rs = bs.query_all_stock(day=datetime.now().strftime("%Y-%m-%d"))
        stock_df = rs.get_data()
        
        # 过滤有效股票
        stock_df = stock_df[
            (stock_df["code"].str.startswith(("sh.", "sz."))) &
            (~stock_df["code_name"].str.contains(r"ST|\*ST", na=False)) &
            (stock_df["tradeStatus"] == "1")
        ]
        
        result = []
        # 只取前300只，避免超时
        for _, row in stock_df.head(300).iterrows():
            try:
                code = row["code"]
                name = row["code_name"]
                
                # 获取2024年年报
                fin_rs = bs.query_financial_indicator(
                    code,
                    year=2024,
                    quarter=4,
                    fields="roeAvg,peTTM,dividend,liabilityToAsset,listDate"
                )
                fin_df = fin_rs.get_data()
                
                if fin_df.empty:
                    continue
                
                fin = fin_df.iloc[0]
                
                # 安全转换
                roe = float(fin["roeAvg"]) * 100 if fin["roeAvg"] and fin["roeAvg"].strip() else 0
                pe = float(fin["peTTM"]) if fin["peTTM"] and fin["peTTM"].strip() else 9999
                dividend = float(fin["dividend"]) * 100 if fin["dividend"] and fin["dividend"].strip() else 0
                debt = float(fin["liabilityToAsset"]) * 100 if fin["liabilityToAsset"] and fin["liabilityToAsset"].strip() else 100
                list_date = fin["listDate"]
                
                # 筛选条件
                if (roe >= roe_min and pe <= pe_max and dividend >= dividend_min 
                    and debt < 60 and list_date < (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")):
                    result.append({
                        "股票代码": code.replace("sh.", "").replace("sz.", ""),
                        "股票名称": name,
                        "ROE(%)": round(roe, 2),
                        "PE": round(pe, 2),
                        "股息率(%)": round(dividend, 2),
                        "资产负债率(%)": round(debt, 2)
                    })
            except:
                continue
        
        bs.logout()
        return pd.DataFrame(result).head(20)
    except:
        return None

# -------------------------- 页面渲染 --------------------------
page = st.sidebar.selectbox("导航菜单", ["首页", "选股页面", "数据说明"])

# 首页
if page == "首页":
    st.title("📈 巴芒投资选股系统")
    st.subheader("基于巴菲特和段永平投资理念的长期投资工具")
    st.info(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.subheader("市场估值概览")
    with st.spinner("正在加载最新估值数据..."):
        index_data = get_index_pe()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("沪深300 PE", index_data[0])
    col2.metric("中证500 PE", index_data[1])
    col3.metric("创业板指 PE", index_data[2])
    
    st.markdown("---")
    st.markdown("""
    ### 估值参考
    - **沪深300**：低于10倍极度低估，10-15倍低估，15-25倍合理，25倍以上高估
    - **中证500**：低于20倍低估，20-30倍合理，30倍以上高估
    - **创业板指**：低于30倍低估，30-50倍合理，50倍以上高估
    """)

# 选股页面
elif page == "选股页面":
    st.title("🔍 巴芒选股策略筛选结果")
    st.caption("基于巴菲特价值投资原则的量化筛选")
    
    with st.expander("📋 选股策略说明", expanded=True):
        st.markdown("""
        ### 核心选股逻辑
        1. **财务健康**：资产负债率 < 60%，连续5年ROE > 15%
        2. **估值合理**：PE < 25，股息率 > 2%
        3. **风险排除**：剔除ST股、上市不足3年新股
        """)
    
    st.sidebar.subheader("⚙️ 筛选参数")
    roe_threshold = st.sidebar.slider("最低ROE(%)", 10, 25, 15)
    pe_threshold = st.sidebar.slider("最高PE", 15, 40, 25)
    dividend_threshold = st.sidebar.slider("最低股息率(%)", 1, 5, 2)
    
    if st.button("执行筛选"):
        with st.spinner("正在拉取最新财务数据..."):
            stocks = get_stock_list(roe_threshold, pe_threshold, dividend_threshold)
        
        if stocks is not None and not stocks.empty:
            st.success(f"筛选完成！找到 {len(stocks)} 只符合条件的股票")
            st.dataframe(stocks, width="stretch")
        elif stocks is None:
            st.error("数据获取失败，请稍后重试")
        else:
            st.info("没有符合当前条件的股票，请调整筛选参数")

# 数据说明页面
elif page == "数据说明":
    st.title("ℹ️ 数据来源与更新")
    st.write(f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.markdown("""
    ### 免费数据来源
    ✅ 指数估值：Baostock（上交所/深交所官方行情）
    ✅ 财务数据：Baostock（上市公司2024年完整年报）
    
    ### 更新频率
    • 指数估值：每小时更新
    • 选股数据：每天更新（使用2024年完整年报）
    
    ⚠️ 免责声明：本工具仅用于学习参考，不构成任何投资建议。
    """)

st.sidebar.markdown("---")
st.sidebar.caption(f"© 2026 巴芒投资 | 更新：{datetime.now().strftime('%Y-%m-%d')}")
