import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="巴芒段投资逻辑选股系统", layout="wide")
st.title("巴菲特 + 芒格 + 段永平 投资逻辑选股系统")

@st.cache_data(ttl=3600)
def fetch_large_stock_pool():
    """获取大盘股票列表"""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'JPM', 'JNJ', 'V'
    ]

def get_financial_data(ticker):
    """获取财务数据"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            'name': info.get('longName', ticker),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'market_cap': info.get('marketCap', 0),
            'current_price': info.get('currentPrice', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'pb_ratio': info.get('priceToBook', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'avg_roe': info.get('returnOnEquity', 0),
            'avg_gross_margin': info.get('grossMargins', 0),
            'avg_net_margin': info.get('profitMargins', 0),
            'debt_to_equity': info.get('debtToEquity', 0),
            'current_ratio': info.get('currentRatio', 0),
            'revenue_growth': info.get('revenueGrowth', 0),
            'earnings_growth': info.get('earningsGrowth', 0),
        }
    except Exception as e:
        st.error(f"获取{ticker}数据失败: {e}")
        return None

def layer_one_munger_logic(stock_info):
    """第一层：芒格商业模式筛选"""
    avg_roe = stock_info.get('avg_roe', 0)
    avg_gross_margin = stock_info.get('avg_gross_margin', 0)
    avg_net_margin = stock_info.get('avg_net_margin', 0)
    
    # 筛选条件
    roe_condition = avg_roe >= 0.15
    gross_margin_condition = avg_gross_margin >= 0.30
    net_margin_condition = avg_net_margin >= 0.10
    
    return {
        'pass': roe_condition and gross_margin_condition and net_margin_condition,
        'details': {
            'ROE': f"{avg_roe:.2%}",
            '毛利率': f"{avg_gross_margin:.2%}",
            '净利率': f"{avg_net_margin:.2%}",
            'ROE达标': '✅' if roe_condition else '❌',
            '毛利率达标': '✅' if gross_margin_condition else '❌',
            '净利率达标': '✅' if net_margin_condition else '❌'
        }
    }

def layer_two_duan_logic(stock_info):
    """第二层：段永平企业文化筛选"""
    # 简化的企业文化评估
    debt_to_equity = stock_info.get('debt_to_equity', 0)
    earnings_growth = stock_info.get('earnings_growth', 0)
    
    # 假设评分系统
    culture_score = 8.0  # 默认8分
    
    # 债务水平影响评分
    if debt_to_equity > 100:
        culture_score -= 2.0
    elif debt_to_equity > 50:
        culture_score -= 1.0
        
    # 盈利增长影响评分
    if earnings_growth < 0:
        culture_score -= 1.0
    elif earnings_growth < 0.05:
        culture_score -= 0.5
        
    return {
        'pass': culture_score >= 7.0,
        'details': {
            '企业文化评分': f"{culture_score:.1f}",
            '评分达标': '✅' if culture_score >= 7.0 else '❌'
        }
    }

def layer_three_buffett_logic(stock_info):
    """第三层：巴菲特护城河筛选"""
    pe_ratio = stock_info.get('pe_ratio', 0)
    pb_ratio = stock_info.get('pb_ratio', 0)
    market_cap = stock_info.get('market_cap', 0)
    
    # 估值筛选
    undervalued_pe = pe_ratio > 0 and pe_ratio < 25
    undervalued_pb = pb_ratio > 0 and pb_ratio < 3.0
    
    return {
        'pass': undervalued_pe and undervalued_pb,
        'details': {
            'PE比率': f"{pe_ratio:.2f}" if pe_ratio > 0 else "N/A",
            'PB比率': f"{pb_ratio:.2f}" if pb_ratio > 0 else "N/A",
            'PE估值合理': '✅' if undervalued_pe else '❌',
            'PB估值合理': '✅' if undervalued_pb else '❌'
        }
    }

def main():
    st.sidebar.header("筛选参数设置")
    
    # 允许的行业
    allowed_sectors = st.sidebar.multiselect(
        "选择允许的行业",
        options=[
            "Technology", "Healthcare", "Consumer Cyclical", 
            "Consumer Defensive", "Financial Services", 
            "Communication Services", "Industrials", "Energy"
        ],
        default=["Technology", "Healthcare", "Consumer Defensive"]
    )
    
    # 开始分析按钮
    if st.button("开始分析"):
        with st.spinner("正在分析股票..."):
            large_pool = fetch_large_stock_pool()
            results = []
            
            for i, ticker in enumerate(large_pool):
                progress = (i + 1) / len(large_pool)
                st.progress(progress, text=f"正在分析 {ticker} ({i+1}/{len(large_pool)})")
                
                stock_info = get_financial_data(ticker)
                if not stock_info:
                    continue
                
                # 三层筛选
                mung_result = layer_one_munger_logic(stock_info)
                duan_result = layer_two_duan_logic(stock_info)
                buff_result = layer_three_buffett_logic(stock_info)
                
                overall_pass = mung_result['pass'] and duan_result['pass'] and buff_result['pass']
                
                if overall_pass:
                    results.append({
                        '股票代码': ticker,
                        '公司名称': stock_info['name'],
                        '行业': stock_info['industry'],
                        '当前价格': f"${stock_info['current_price']:.2f}",
                        '市值': f"${stock_info['market_cap']/1e9:.2f}B" if stock_info['market_cap'] > 0 else "N/A",
                        '最终通过': '✅' if overall_pass else '❌'
                    })
            
            if results:
                df_results = pd.DataFrame(results)
                st.success(f"找到 {len(df_results)} 只符合条件的股票")
                st.dataframe(df_results, use_container_width=True)
                
                # 显示详细分析
                for result in results[:3]:  # 只显示前3只的详细分析
                    ticker = result['股票代码']
                    stock_info = get_financial_data(ticker)
                    
                    with st.expander(f"详细分析 - {ticker} ({result['公司名称']})"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.subheader("芒格筛选结果")
                            mung_result = layer_one_munger_logic(stock_info)
                            for key, value in mung_result['details'].items():
                                st.write(f"{key}: {value}")
                            
                        with col2:
                            st.subheader("段永平筛选结果")
                            duan_result = layer_two_duan_logic(stock_info)
                            for key, value in duan_result['details'].items():
                                st.write(f"{key}: {value}")
                                
                        with col3:
                            st.subheader("巴菲特筛选结果")
                            buff_result = layer_three_buffett_logic(stock_info)
                            for key, value in buff_result['details'].items():
                                st.write(f"{key}: {value}")
            else:
                st.warning("没有找到符合条件的股票")

if __name__ == "__main__":
    main()
