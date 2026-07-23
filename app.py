import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="スイングトレード分析システム", layout="wide")

# ==========================================
# 🎨 CSS（スマホ最適化・レスポンシブ）
# ==========================================
st.markdown("""
<style>
header { background-color: transparent !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.block-container { padding-top: 1.5rem; }
.stApp { background-color: #F4F6F8; }

.alert-banner { background-color: #FCE8E6; color: #B31412; padding: 16px 20px; border-radius: 4px; border-left: 4px solid #B31412; margin-bottom: 24px; display: flex; align-items: flex-start; gap: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }

.overall-summary-card { background-color: #1A73E8; color: #FFFFFF; border-radius: 8px; padding: 20px 24px; margin-bottom: 24px; box-shadow: 0 2px 6px rgba(25,103,210,0.25); }
.overall-summary-title { font-size: 18px; font-weight: bold; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.overall-summary-text { font-size: 15px; line-height: 1.6; opacity: 0.95; }

.individual-advice-title { font-size: 16px; font-weight: bold; color: #202124; margin-bottom: 12px; }
.ai-advice-card { background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E8EAED; padding: 18px 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.ai-advice-header { color: #1967D2; font-size: 16px; font-weight: bold; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
.ai-action-box { background-color: #FAFAFA; border: 1px solid #E8EAED; border-radius: 6px; padding: 12px; margin-top: 8px; }

.ranking-card { background-color: #FFFFFF; border-radius: 8px; padding: 24px; border: 1px solid #E8EAED; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.ranking-title { font-size: 18px; font-weight: bold; color: #202124; margin-bottom: 20px; }

.table-responsive { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
.custom-table { width: 100%; border-collapse: collapse; text-align: left; min-width: 600px; }
.custom-table th { color: #5F6368; font-weight: normal; font-size: 13px; padding: 12px 8px; border-bottom: 1px solid #E8EAED; white-space: nowrap; }
.custom-table td { padding: 16px 8px; border-bottom: 1px solid #E8EAED; vertical-align: middle; color: #202124; font-size: 14px; white-space: nowrap; }

.badge-green { background-color: #E6F4EA; color: #137333; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: bold; display: inline-block; }
.badge-gray { background-color: #F1F3F4; color: #5F6368; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: bold; display: inline-block; }
.badge-blue { background-color: #E8F0FE; color: #1967D2; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: bold; display: inline-block; margin-right: 4px; }
.badge-yellow { background-color: #FEF7E0; color: #B06000; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: bold; display: inline-block; }
.badge-red { background-color: #FCE8E6; color: #C5221F; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: bold; display: inline-block; }

.metric-card { background-color: #FFFFFF; border-radius: 8px; padding: 24px 20px; border: 1px solid #E8EAED; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; position: relative; }
.metric-info { display: flex; flex-direction: column; }
.metric-title { color: #5F6368; font-size: 13px; margin-bottom: 8px; font-weight: bold; }
.metric-value { color: #202124; font-size: 22px; font-weight: bold; }
.color-up { color: #0F9D58; }
.color-down { color: #D23F31; }
.icon-circle { min-width: 44px; height: 44px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 20px; }
.icon-blue { background-color: #E8F0FE; }
.icon-green { background-color: #E6F4EA; }
.icon-yellow { background-color: #FEF7E0; }
.icon-purple { background-color: #F3E8FD; }

@media (max-width: 768px) {
    .metric-card { flex-direction: column; align-items: flex-start; padding: 16px; }
    .icon-circle { position: absolute; right: 16px; top: 16px; }
    .custom-table th, .custom-table td { padding: 10px 4px; font-size: 13px; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 📊 Googleスプレッドシート連携機能
# ==========================================
@st.cache_resource
def get_gspread_sheet():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(st.secrets["spreadsheet_url"]).sheet1
        return sheet
    except Exception as e:
        st.error(f"スプレッドシート接続エラー: {e}")
        return None

def load_data_from_sheet():
    sheet = get_gspread_sheet()
    if not sheet:
        return {"portfolio": [], "cash_balance": 0.0, "total_invested": 0.0, "history_dict": {}}
    
    try:
        records = sheet.get_all_records()
        portfolio = []
        cash_balance = 0.0
        total_invested = 0.0
        history_dict = {}
        
        for i, r in enumerate(records):
            if i == 0:
                try:
                    cb = r.get("_cash_balance", "")
                    cash_balance = float(cb) if cb != "" else 0.0
                    ti = r.get("_total_invested", "")
                    total_invested = float(ti) if ti != "" else 0.0
                    hd = r.get("_history_dict", "")
                    history_dict = json.loads(hd) if hd != "" else {}
                except:
                    pass

            code = str(r.get("コード", "")).strip()
            if code:
                portfolio.append({
                    "コード": code,
                    "銘柄名": str(r.get("銘柄名", "")),
                    "買値": float(r.get("買値", 0) if r.get("買値", "") != "" else 0),
                    "株数": int(r.get("株数", 0) if r.get("株数", "") != "" else 0),
                    "購入日": str(r.get("購入日", ""))
                })
                
        if total_invested == 0.0 and len(portfolio) > 0:
            for p in portfolio:
                total_invested += float(p["買値"]) * int(p["株数"])
                
        return {"portfolio": portfolio, "cash_balance": cash_balance, "total_invested": total_invested, "history_dict": history_dict}
    except Exception as e:
        return {"portfolio": [], "cash_balance": 0.0, "total_invested": 0.0, "history_dict": {}}

def save_data_to_sheet():
    sheet = get_gspread_sheet()
    if not sheet: return
    
    try:
        sheet.clear()
        header = ["コード", "銘柄名", "買値", "株数", "購入日", "_cash_balance", "_total_invested", "_history_dict"]
        rows = [header]
        
        count = max(1, len(st.session_state.portfolio))
        for i in range(count):
            if i < len(st.session_state.portfolio):
                p = st.session_state.portfolio[i]
                row = [
                    str(p.get("コード", "")),
                    str(p.get("銘柄名", "")),
                    p.get("買値", 0),
                    p.get("株数", 0),
                    str(p.get("購入日", ""))
                ]
            else:
                row = ["", "", "", "", ""]
                
            if i == 0:
                row.extend([
                    st.session_state.cash_balance,
                    st.session_state.total_invested,
                    json.dumps(st.session_state.history_dict)
                ])
            else:
                row.extend(["", "", ""])
                
            rows.append(row)
            
        sheet.update('A1', rows)
    except Exception as e:
        st.error(f"スプレッドシート書き込みエラー: {e}")

if "data_loaded" not in st.session_state:
    saved_data = load_data_from_sheet()
    st.session_state.portfolio = saved_data["portfolio"]
    st.session_state.cash_balance = saved_data.get("cash_balance", 0.0)
    st.session_state.total_invested = saved_data.get("total_invested", 0.0)
    st.session_state.history_dict = saved_data.get("history_dict", {})
    st.session_state.confirm_sell_idx = None
    st.session_state.data_loaded = True

# ==========================================
# 🧠 AI分析関数
# ==========================================
def analyze_news_sentiment(news_list):
    if not news_list: return 0.0
    positive_words = ['profit', 'growth', 'up', 'buy', 'positive', 'surge', 'record', 'dividend', '増益', '上方修正', '好調', '買収', '上昇', '新製品']
    negative_words = ['loss', 'down', 'sell', 'negative', 'drop', 'cut', 'miss', 'decline', '減益', '下方修正', '不調', '下落', '赤字', '悪化']
    score = 0
    valid_articles = 0
    for article in news_list:
        title = article.get('title', '').lower()
        if not title: continue
        valid_articles += 1
        for w in positive_words:
            if w in title: score += 1
        for w in negative_words:
            if w in title: score -= 1
    if valid_articles == 0: return 0.0
    return max(min(score / valid_articles, 1.0), -1.0)

@st.cache_data(ttl=900)
def get_advanced_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(f"{ticker_symbol}.T")
        df = ticker.history(period='6mo')
        df = df.dropna()
        if df.empty or len(df) < 25: return None
        
        close = float(df['Close'].iloc[-1])
        if np.isnan(close): return None
        
        score = 40
        sma25 = df['Close'].rolling(window=25).mean().iloc[-1]
        if close > sma25: score += 20
        else: score += 10
            
        delta = df['Close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean()
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        if 40 <= rsi <= 60: score += 25
        elif rsi < 40: score += 30
        else: score += 10

        news = ticker.news
        sentiment = analyze_news_sentiment(news)
        final_score = min(max(int(score + (sentiment * 15)), 0), 100)

        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        atr = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean().iloc[-1]

        target_multiplier = 2.0 + (sentiment * 1.0)
        stop_multiplier = 1.5 - (sentiment * 0.5)
        
        dynamic_target = close + (atr * target_multiplier)
        dynamic_stop = close - (atr * stop_multiplier)

        buy_min = round(close - (atr * 0.6), -1)
        buy_max = round(close + (atr * 0.2), -1)

        return {
            "close": close, "score": final_score, "sentiment": sentiment,
            "dynamic_target": round(dynamic_target, -1), "dynamic_stop": round(dynamic_stop, -1),
            "buy_min": buy_min, "buy_max": buy_max
        }
    except:
        return None

# ==========================================
# ⚙️ サイドバー
# ==========================================
st.sidebar.markdown("### 🔄 データの更新")
if st.sidebar.button("最新の株価・AI判定を取得", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.divider()

st.sidebar.header("💼 保有中の銘柄（売却）")
if not st.session_state.portfolio:
    st.sidebar.info("保有銘柄はありません。下のフォームから追加してください。")
else:
    for i, p in enumerate(st.session_state.portfolio):
        st.sidebar.markdown(f"**{p['コード']} {p['銘柄名']}**")
        
        if st.session_state.confirm_sell_idx == i:
            st.sidebar.warning("⚠️ 本当に売却しますか？内容を確認してください。")
            latest_data = get_advanced_stock_data(p['コード'])
            default_sell_price = int(latest_data['close']) if latest_data else int(p['買値'])
            
            sell_price = st.sidebar.number_input(f"実際の売却価格(円)", min_value=0, step=1, value=default_sell_price, key=f"sp_{i}")
            sell_shares = st.sidebar.number_input(f"売却する株数", min_value=1, max_value=int(p['株数']), step=1, value=int(p['株数']), key=f"ss_{i}")
            
            col_ok, col_cancel = st.sidebar.columns(2)
            with col_ok:
                if st.button("✔️ 確定", type="primary", key=f"ok_{i}", use_container_width=True):
                    st.session_state.cash_balance += (sell_price * sell_shares)
                    st.session_state.portfolio[i]['株数'] -= sell_shares
                    if st.session_state.portfolio[i]['株数'] <= 0:
                        st.session_state.portfolio.pop(i)
                    st.session_state.confirm_sell_idx = None
                    save_data_to_sheet()
                    st.rerun()
            with col_cancel:
                if st.button("❌ 戻る", key=f"cancel_{i}", use_container_width=True):
                    st.session_state.confirm_sell_idx = None
                    st.rerun()
        else:
            col_info, col_btn = st.sidebar.columns([6, 4])
            with col_info:
                st.markdown(f"<div style='font-size:12px; color:#5F6368; padding-top:6px;'>買値: {p['買値']:,.0f}円<br>保有: {p['株数']}株</div>", unsafe_allow_html=True)
            with col_btn:
                if st.button("売却", key=f"btn_{i}", use_container_width=True):
                    st.session_state.confirm_sell_idx = i
                    st.rerun()
        st.sidebar.divider()

st.sidebar.header("➕ 新規銘柄の追加")
with st.sidebar.form("add_stock_form", clear_on_submit=True):
    new_code = st.text_input("銘柄コード (例: 7203)")
    new_name = st.text_input("銘柄名 (例: トヨタ自動車)")
    new_buy = st.number_input("買値 (円)", min_value=0, step=1, value=0)
    new_shares = st.number_input("株数", min_value=1, step=1, value=100)
    new_date = st.date_input("購入日", value=date.today())
    
    if st.form_submit_button("ポートフォリオに追加"):
        if new_code and new_name and new_buy > 0:
            cost = new_buy * new_shares
            if cost > st.session_state.cash_balance:
                st.session_state.total_invested += (cost - st.session_state.cash_balance)
                st.session_state.cash_balance = 0.0
            else:
                st.session_state.cash_balance -= cost
            st.session_state.portfolio.append({
                "コード": new_code, 
                "銘柄名": new_name, 
                "買値": new_buy, 
                "株数": new_shares,
                "購入日": new_date.strftime("%Y-%m-%d")
            })
            save_data_to_sheet()
            st.rerun()

# ==========================================
# 📊 データ集計 ＆ 全銘柄アドバイス生成
# ==========================================
nikkei_majors = [{"code": "7203", "name": "トヨタ自動車"}, {"code": "9984", "name": "ソフトバンクG"}, {"code": "9983", "name": "ファーストリテイリング"}, {"code": "6861", "name": "キーエンス"}, {"code": "8035", "name": "東京エレクトロン"}, {"code": "6758", "name": "ソニーグループ"}, {"code": "8306", "name": "三菱ＵＦＪ"}, {"code": "8766", "name": "東京海上HD"}, {"code": "9432", "name": "ＮＴＴ"}, {"code": "4063", "name": "信越化学工業"}]
candidates = []
for stock in nikkei_majors:
    data = get_advanced_stock_data(stock["code"])
    if data: 
        candidates.append({
            "コード": stock["code"], "銘柄名": stock["name"], "スコア": data["score"], 
            "現在値": data["close"], "利確目安": data["dynamic_target"],
            "buy_min": data["buy_min"], "buy_max": data["buy_max"]
        })
candidates.sort(key=lambda x: x["スコア"], reverse=True)
top_candidate = candidates[0] if candidates else None

current_portfolio_value = 0
current_holdings_profit = 0
alerts = []
portfolio_details = []
individual_advices = [] 

for p in st.session_state.portfolio:
    ticker = str(p["コード"]).strip()
    name = str(p["銘柄名"]).strip()
    buy_price = float(p["買値"])
    shares = int(p["株数"])
    
    buy_date_str = p.get("購入日")
    days_held = None
    if buy_date_str:
        try:
            buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d').date()
            days_held = (date.today() - buy_date).days + 1
        except:
            pass

    data = get_advanced_stock_data(ticker)
    if data:
        current_val = data["close"] * shares
        profit = current_val - (buy_price * shares)
        profit_pct = (data["close"] / buy_price - 1) * 100
        current_portfolio_value += current_val
        current_holdings_profit += profit
        
        ai_target = data["dynamic_target"]
        ai_stop = data["dynamic_stop"]

        if data["close"] >= ai_target:
            alerts.append({"type": "利確", "name": name, "code": ticker, "target": ai_target})
            status_tag = "🎯 利確到達"
            action_text = f"目標ライン（{ai_target:,.0f}円）に到達しました。利益確定（一部または全売却）をおすすめします。"
        elif data["close"] <= ai_stop:
            alerts.append({"type": "損切", "name": name, "code": ticker, "target": ai_stop})
            status_tag = "⚠️ 損切到達"
            action_text = f"撤退ライン（{ai_stop:,.0f}円）に到達しました。リスク管理のため売却・損失限定を検討してください。"
        elif top_candidate and data["score"] < top_candidate["スコア"] - 15 and top_candidate["スコア"] >= 80:
            status_tag = "🔄 乗り換え検討"
            action_text = f"現在のAIスコアは{data['score']}点です。ランキング1位の【{top_candidate['銘柄名']}】（スコア{top_candidate['スコア']}点）の方が勢いが高いため、乗り換えを検討するのも一手です。"
        else:
            status_tag = "✊ 保有継続"
            action_text = f"AIスコアは{data['score']}点で安定しています。目標利確ライン（{ai_target:,.0f}円）を目指して引き続き保有をおすすめします。"

        individual_advices.append({
            "code": ticker, "name": name, "profit_pct": profit_pct, 
            "score": data["score"], "status_tag": status_tag, "action_text": action_text,
            "days_held": days_held
        })

        portfolio_details.append({
            "ticker": ticker, "name": name, "buy_price": buy_price, "shares": shares, 
            "current_price": data["close"], "current_val": current_val, "profit": profit, 
            "profit_pct": profit_pct, "target": ai_target, "stop": ai_stop, "score": data["score"],
            "days_held": days_held
        })

total_assets = st.session_state.cash_balance + current_portfolio_value
total_return = total_assets - st.session_state.total_invested

current_month = pd.Timestamp.today().strftime('%Y-%m')
if st.session_state.history_dict.get(current_month) != total_assets:
    st.session_state.history_dict[current_month] = total_assets
    if len(st.session_state.portfolio) > 0 or st.session_state.total_invested > 0 or st.session_state.cash_balance > 0:
        save_data_to_sheet()

if not portfolio_details:
    overall_text = "現在保有している銘柄はありません。AIスコアランキングで「買い推奨」が出ている銘柄をチェックして新規ポジションの検討を行いましょう。"
else:
    has_alert = len(alerts) > 0
    if has_alert:
        overall_text = f"現在、保有銘柄の中で【{alerts[0]['name']}】が重要なライン（{alerts[0]['type']}ライン）に到達しています。該当銘柄のアクションを優先し、ポートフォリオのリスク整理・利益確定を行いましょう。"
    elif current_holdings_profit >= 0:
        overall_text = f"保有株全体で +{current_holdings_profit:,.0f}円 の含み益が出ており、順調な推移です。全銘柄とも急な売却の必要はありません。個別の利確ライン到達を待ちつつ、安定保有を継続してください。"
    else:
        overall_text = f"保有株全体で {current_holdings_profit:,.0f}円 の評価損となっています。AI損切ラインに到達していないか確認しつつ、ランキング上位の高スコア銘柄への一部乗り換え等でポートフォリオの立て直しを検討しましょう。"

# ==========================================
# 🖥️ 画面描画
# ==========================================
# メイン画面ヘッダーエリア（右端にグルグルマーク更新ボタンを追加）
col_head, col_refresh = st.columns([8.5, 1.5])
with col_head:
    st.caption("スイングトレード AI分析＆ポートフォリオ管理")
with col_refresh:
    if st.button("🔄", key="main_refresh_btn", help="最新データに更新"):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3 = st.tabs(["❖ 総合ダッシュボード", "💼 ポートフォリオ", "📊 運用サマリー"])

with tab1:
    for al in alerts:
        st.markdown(f'<div class="alert-banner"><div class="alert-icon">🔔</div><div><div class="alert-content-title">AI動的{al["type"]}アラート</div><div class="alert-content-text">【{al["code"]} {al["name"]}】が目標{al["type"]}ライン（{al["target"]:,.0f}円）に到達しました。</div></div></div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-info"><div class="metric-title">現在の総資産 (現金＋株式)</div><div class="metric-value">{total_assets:,.0f} 円</div></div><div class="icon-circle icon-blue">💰</div></div>', unsafe_allow_html=True)
    with col2:
        r_class, r_sign = ("color-up", "+") if total_return >= 0 else ("color-down", "")
        st.markdown(f'<div class="metric-card"><div class="metric-info"><div class="metric-title">全期間トータルリターン</div><div class="metric-value {r_class}">{r_sign}{total_return:,.0f} <span style="font-size:14px;">円</span></div></div><div class="icon-circle icon-green">📈</div></div>', unsafe_allow_html=True)
    with col3:
        h_class, h_sign = ("color-up", "+") if current_holdings_profit >= 0 else ("color-down", "")
        st.markdown(f'<div class="metric-card"><div class="metric-info"><div class="metric-title">保有株の評価損益</div><div class="metric-value {h_class}">{h_sign}{current_holdings_profit:,.0f} <span style="font-size:14px;">円</span></div></div><div class="icon-circle icon-yellow">📊</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-info"><div class="metric-title">保有銘柄数</div><div class="metric-value">{len(portfolio_details)} <span style="font-size:14px; font-weight:normal;">銘柄</span></div></div><div class="icon-circle icon-purple">💼</div></div>', unsafe_allow_html=True)

    st.markdown(f'<div class="overall-summary-card"><div class="overall-summary-title">🌐 AI ポートフォリオ全体総評</div><div class="overall-summary-text">{overall_text}</div></div>', unsafe_allow_html=True)

    if individual_advices:
        st.markdown('<div class="individual-advice-title">📦 保有銘柄ごとのAI個別アドバイス</div>', unsafe_allow_html=True)
        for adv in individual_advices:
            sign = "+" if adv['profit_pct'] > 0 else ""
            p_color = "#0F9D58" if adv['profit_pct'] >= 0 else "#D23F31"
            days_badge = f"<span class='badge-blue'>保有 {adv['days_held']}日目</span>" if adv['days_held'] else ""
            st.markdown(f'<div class="ai-advice-card"><div class="ai-advice-header"><div>【{adv["code"]} {adv["name"]}】 <span style="font-size:13px; color:{p_color}; font-weight:normal;">損益: {sign}{adv["profit_pct"]:.1f}%</span></div><div>{days_badge}<span class="badge-gray">{adv["status_tag"]}</span></div></div><div style="font-size:13px; color:#5F6368; margin-bottom:6px;">AIスコア: <strong>{adv["score"]}点</strong></div><div class="ai-action-box"><div style="font-size:14px; color:#202124;">{adv["action_text"]}</div></div></div>', unsafe_allow_html=True)

    html_table = '<div class="ranking-card"><div class="ranking-title">日経225主要銘柄 AIスコアランキング</div><div class="table-responsive"><table class="custom-table"><tr><th>順位</th><th>銘柄</th><th>現在値 (推奨買値)</th><th>AI利確目安</th><th>AIスコア</th><th>推奨アクション</th></tr>'
    for idx, cand in enumerate(candidates):
        rank = idx + 1
        badge = '<span class="badge-green">買い推奨</span>' if cand["スコア"] >= 80 else '<span class="badge-gray">監視</span>'
        html_table += f'<tr><td style="font-weight:bold; color:#9AA0A6;">{rank}</td><td><div style="font-weight:bold; color:#1967D2;">{cand["銘柄名"]}</div><div style="font-size:12px; color:#5F6368;">{cand["コード"]}</div></td><td><div style="font-weight:bold; color:#202124;">{cand["現在値"]:,.1f}円</div><div style="font-size:12px; color:#5F6368;">(目安: {cand["buy_min"]:,.0f}〜{cand["buy_max"]:,.0f}円)</div></td><td style="font-weight:bold; color:#B06000;">{cand["利確目安"]:,.0f}円</td><td><span style="font-weight:bold; font-size:16px;">{cand["スコア"]}</span><div style="width:100px; background-color:#E8EAED; border-radius:4px; height:6px; display:inline-block; margin-left:8px;"><div style="background-color:#4285F4; height:100%; border-radius:4px; width:{cand["スコア"]}%;"></div></div></td><td>{badge}</td></tr>'
    html_table += '</table></div></div><br>'
    st.markdown(html_table, unsafe_allow_html=True)

with tab2:
    if not portfolio_details:
        st.info("保有銘柄はありません。")
    else:
        st.markdown('<div style="margin-bottom:12px; color:#5F6368; font-size:14px;">※ 以下の「利確・損切ライン」は、相場のボラティリティ(ATR)とニュースセンチメントを加味し、<strong style="color:#1967D2;">AIが毎日自動で再計算・更新</strong>しています。</div>', unsafe_allow_html=True)
        html_port = '<div class="ranking-card"><div class="table-responsive"><table class="custom-table"><tr><th>銘柄</th><th>買値 / 株数</th><th>現在値</th><th>損益</th><th>AIスコア</th><th>AI判定</th></tr>'
        for p in portfolio_details:
            if p['current_price'] >= p['target']: badge = '<span class="badge-yellow">利確到達</span>'
            elif p['current_price'] <= p['stop']: badge = '<span class="badge-red">損切到達</span>'
            else: badge = '<span class="badge-gray">保有継続</span>'
            r_diff = p['target'] - p['stop']
            prog_pct = min(max((p['current_price'] - p['stop']) / r_diff * 100, 0.0), 100.0) if r_diff > 0 else 50.0
            p_color, p_sign = ("color-up", "+") if p['profit'] >= 0 else ("color-down", "")
            days_str = f" <br><span style='font-size:12px; font-weight:bold; color:#1967D2;'>(保有 {p['days_held']}日目)</span>" if p['days_held'] else ""
            
            html_port += f'<tr><td><div style="font-weight:bold; color:#202124;">{p["name"]}</div><div style="font-size:12px; color:#5F6368;">{p["ticker"]}</div></td><td><div style="font-size:15px; color:#202124;">{p["buy_price"]:,.0f}円</div><div style="font-size:13px; color:#5F6368;">{p["shares"]}株{days_str}</div></td><td><div style="font-size:16px; font-weight:bold; color:#202124;">{p["current_price"]:,.1f}円</div></td><td><div class="{p_color}" style="font-size:16px; font-weight:bold;">{p_sign}{p["profit"]:,.0f}円</div><div class="{p_color}" style="font-size:13px;">({p_sign}{p["profit_pct"]:.1f}%)</div></td><td><div style="font-size:16px; font-weight:bold; color:#202124;">{p["score"]}<span style="font-size:13px; font-weight:normal; color:#5F6368;">点</span></div></td><td>{badge}</td></tr><tr><td colspan="6" style="padding: 0; border-bottom: 1px solid #E8EAED;"><div style="display:flex; align-items:center; padding: 12px 16px; background-color:#FAFAFA; font-size:12px; color:#5F6368;"><div style="width:70px; text-align:right;">AI損切<br><span style="font-size:14px; font-weight:bold; color:#202124;">{p["stop"]:,.0f}円</span></div><div style="flex-grow:1; height:6px; background-color:#E8EAED; border-radius:3px; margin: 0 16px; position:relative;"><div style="position:absolute; left: {prog_pct}%; top:-4px; width:14px; height:14px; background-color:#1967D2; border-radius:50%; box-shadow: 0 1px 3px rgba(0,0,0,0.3); transform: translateX(-50%);"></div></div><div style="width:70px; text-align:left;">AI利確<br><span style="font-size:14px; font-weight:bold; color:#202124;">{p["target"]:,.0f}円</span></div></div></td></tr>'
        html_port += '</table></div></div>'
        st.markdown(html_port, unsafe_allow_html=True)

with tab3:
    st.header("■ 運用サマリー (月次資産推移)")
    if len(st.session_state.history_dict) <= 1 and list(st.session_state.history_dict.values())[0] == 0:
        st.info("💡 スプレッドシート連携が完了しました。運用実績が蓄積されると、ここに月ごとの資産推移グラフが生成されます。")
    else:
        df_history = pd.DataFrame(list(st.session_state.history_dict.items()), columns=["月", "総資産額(円)"]).set_index("月")
        st.line_chart(df_history)
