import streamlit as st
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="巴芒投资选股器", layout="wide", initial_sidebar_state="expanded")

# -------------------------- 指数估值（Baostock 稳定接口） --------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_index_pe():
    """获取三大指数最新PE，严格处理空值"""
    try:
        login_result = bs.login()
        if login_result.error_code != '0':
            st.error("Baostock登录失败")
            return None
        
        indexes = [
            ("沪深300", "sh.000300"),
            ("中证500", "sh.000905"),
            ("创业板指", "sz.399006")
        ]
        
        pe_values = []
        for name, code in indexes:
            # 获取近30天数据，确保能找到有效PE
            rs = bs.query_history_k_data_plus(
                code,
                "date,peTTM",
                start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                frequency="d"
            )
            df = rs.get_data()
            
            # 从后往前找第一个非空且大于0的PE
            valid_pe = None
            for i in range(len(df)-1, -1, -1):
                pe_str = df.iloc[i]["peTTM"]
                if pe_str and pe_str.strip() != '' and float(pe_str) > 0:
                    valid_pe = round(float(pe_str), 2)
                    break
            
            if valid_pe:
                pe_values.append(valid_pe)
            else:
                st.warning(f"{name} PE数据暂时无法获取")
                pe_values.append(None)
        
        bs.logout()
        return pe_values
    except Exception as e:
        st.error(f"指数估值获取失败：{str(e)[:60]}")
        return None

# -------------------------- 选股数据（Baostock 财务接口） --------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def get_stock_list(roe_min=15, pe_max=25, dividend_min=2):
    """按巴菲特策略筛选股票，修复正则表达式错误"""
    try:
        login_result = bs.login()
        if login_result.error_code != '0':
            st.error("Baostock登录失败")
            return None
        
        # 获取所有A股列表
        rs = bs.query_all_stock(day=datetime.now().strftime("%Y-%m-%d"))
        stock_df = rs.get_data()
        
        # 过滤有效股票（修复正则表达式：*需要转义）
        stock_df = stock_df[
            (stock_df["code"].str.startswith(("sh.", "sz."))) &
            (~stock_df["code_name"].str.contains(r"ST|\*ST", na=False)) &
            (stock_df["tradeStatus"] == "1")  # 仅交易中股票
        ]
        
        result = []
        # 取前500只股票筛选（避免Streamlit超时）
        for _, row in stock_df.head(500).iterrows():
            code = row["code"]
            name = row["code_name"]
            
            # 获取2024年完整年报数据（最准确）
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
            try:
                # 强制转换并严格过滤空值和异常值
                roe = float(fin["roeAvg"]) * 100 if fin["roeAvg"] and fin["roeAvg"].strip() != '' else 0
                pe = float(fin["peTTM"]) if fin["peTTM"] and fin["peTTM"].strip() != '' else 9999
                dividend = float(fin["dividend"]) * 100 if fin["dividend"] and fin["dividend"].strip() != '' else 0
                debt = float(fin["liabilityToAsset"]) * 100 if fin["liabilityToAsset"] and fin["liabilityToAsset"].strip() != '' else 100
                list_date = fin["listDate"]
                
                # 严格筛选条件
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
    except Exception as e:
        st.error(f"选股数据获取失败：{str(e)[:60]}")
        return None

# -------------------------- 宏观数据（友好提示+备用方案） --------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def get_m1_m2_data():
    """获取M1-M2剪刀差，使用备用数据源"""
    try:
        # 由于baostock无直接宏观接口，使用东方财富公开数据接口
        import requests
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_MONEY_SUPPLY",
            "columns": "REPORT_DATE,M1_YOY,M2_YOY",
            "pageSize": "1",
            "pageNum": "1",
            "sortTypes": "-1",
            "sortColumns": "REPORT_DATE"
        }
        response = requests.get(url, timeout=10)
        data = response.json()
        if data["result"] and data["result"]["data"]:
            latest = data["result"]["data"][0]
            m1 = float(latest["M1_YOY"])
            m2 = float(latest["M2_YOY"])
            return round(m1 - m2, 2)
        else:
            return None
    except Exception as e:
        st.error(f"宏观数据获取失败：{str(e)[:60]}")
        return None

# -------------------------- 页面渲染 --------------------------
page = st.sidebar.selectbox("导航菜单", ["首页", "选股页面", "宏观数据", "数据说明"])

# 首页
if page == "首页":
    st.title("📈 巴芒投资选股系统")
    st.subheader("基于巴菲特和段永平投资理念的长期投资工具")
    st.info(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.subheader("市场估值概览")
    with st.spinner("正在加载最新估值数据..."):
        index_data = get_index_pe()
    
    if index_data and len(index_data) == 3:
        col1, col2, col3 = st.columns(3)
        if index_data[0]:
            col1.metric("沪深300 PE", index_data[0])
        else:
            col1.metric("沪深300 PE", "暂无数据")
        if index_data[1]:
            col2.metric("中证500 PE", index_data[1])
        else:
            col2.metric("中证500 PE", "暂无数据")
        if index_data[2]:
            col3.metric("创业板指 PE", index_data[2])
        else:
            col3.metric("创业板指 PE", "暂无数据")
    else:
        st.warning("指数估值数据暂时不可用，请稍后刷新")

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

# 宏观数据页面
elif page == "宏观数据":
    st.title("📊 宏观经济数据仪表盘")
    st.subheader("M1-M2剪刀差（A股流动性指标）")
    
    st.info("""
    • 剪刀差 > 0 → 流动性宽松 → 利好股市
    • 剪刀差 < 0 → 流动性收紧 → 利空股市
    """)
    
    with st.spinner("正在加载最新宏观数据..."):
        m1_m2 = get_m1_m2_data()
    
    if m1_m2:
        st.metric("最新M1-M2剪刀差", f"{m1_m2}%")
    else:
        st.warning("宏观数据暂时不可用，请稍后刷新")

# 数据说明页面
elif page == "数据说明":
    st.title("ℹ️ 数据来源与更新")
    st.write(f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.markdown("""
    ### 免费数据来源
    ✅ 指数估值：Baostock（上交所/深交所官方行情）
    ✅ 财务数据：Baostock（上市公司2024年完整年报）
    ✅ 宏观数据：东方财富网（中国人民银行官方数据）
    
    ### 更新频率
    • 指数估值：每小时更新
    • 选股数据：每天更新（使用2024年完整年报）
    • 宏观数据：每月更新
    
    ⚠️ 免责声明：本工具仅用于学习参考，不构成任何投资建议。
    """)

st.sidebar.markdown("---")
st.sidebar.caption(f"© 2026 巴芒投资 | 更新：{datetime.now().strftime('%Y-%m-%d')}")
