import streamlit as st

def apply():
    st.markdown('''<style>
:root{--ink:#13283b;--muted:#687b8b;--line:#dde6eb;--teal:#00796c}
.stApp{background:#f3f6f8;color:var(--ink)}
.block-container{max-width:1500px;padding:2rem 2.5rem 3rem}
[data-testid="stHeader"]{background:#f3f6f8}
[data-testid="stSidebar"]{background:#102a3a;color:#e7eff3}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] a,[data-testid="stSidebar"] span{color:#e7eff3}
h1,h2,h3{color:var(--ink);letter-spacing:-.035em}h3{font-size:1.15rem!important}
[data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border-radius:16px}
[data-testid="stBaseButton-primary"]{background:#00796c;border-color:#00796c;border-radius:9px;min-height:44px}
[data-testid="stBaseButton-secondary"]{border-radius:9px;border-color:#d8e2e8}
[data-baseweb="tab-list"]{gap:28px;border-bottom:1px solid var(--line)}
[data-baseweb="tab-highlight"]{background:#00796c}
[data-testid="stWidgetLabel"] p{font-size:12px;font-weight:600;color:#506575}
[data-testid="stCaptionContainer"]{color:#687b8b}
.brandbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;gap:20px}
.brand{display:flex;align-items:center;gap:12px}.brand-icon{width:43px;height:43px;background:#102a3a;color:#fff;border-radius:12px;display:grid;place-items:center;font-size:24px}.brand-name{font-size:21px;font-weight:750;letter-spacing:-.7px}.eyebrow{font-size:10px;letter-spacing:1.6px;color:#758793;font-weight:750;text-transform:uppercase}.badge{display:inline-block;padding:5px 9px;border-radius:6px;font-size:10px;font-weight:750;letter-spacing:.5px;background:#e7f4f0;color:#00705e}.badge.amber{color:#925c00;background:#fff0d0}.badge.red{color:#b52d38;background:#ffebed}.badge.neutral{background:#edf1f5;color:#627383}
.hero{display:flex;justify-content:space-between;align-items:center;margin:22px 0 24px;gap:20px}.hero h1{font-size:32px!important;margin:0;padding:0;font-weight:750}.hero p{font-size:14px;color:#738392;margin:6px 0 0}
.flow{display:grid;grid-template-columns:1fr 28px 1fr 28px 1fr 28px 1fr;align-items:center;background:#fff;border:1px solid var(--line);border-radius:14px;padding:17px 22px;margin-bottom:24px}.flow-step{display:flex;align-items:center;gap:10px}.step-num{border:1px solid #d9e3e8;background:#f5f8fa;border-radius:50%;width:30px;height:30px;display:grid;place-items:center;font-size:11px;color:#617686}.flow strong{font-size:12px;display:block}.flow small{font-size:10px;color:#7b8b97}.arrow{color:#a1b2be}.section-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.section-title{font-weight:750;font-size:15px;letter-spacing:-.3px}.section-id{font-size:10px;color:#78909e;letter-spacing:1px}
.source-title{font-size:19px;line-height:1.3;font-weight:700;margin:15px 0 5px;overflow-wrap:anywhere}.source-meta{font-size:11px;color:#80909c;margin-bottom:18px}.document-reader{background:#fff;color:#243a4b;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.85;font-size:14px;max-height:370px;overflow:auto;padding:8px 5px}.document-reader mark{background:#ffedbf;color:#754d08;border-bottom:2px solid #dda235;border-radius:3px;padding:2px 0}
.signal-note{border-left:3px solid #e5ab3c;background:#fff8e8;padding:10px 13px;font-size:12px;color:#805b1b;margin-top:12px}.scope{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0}.scope span{font-size:10px;border:1px solid #dce6eb;padding:5px 8px;border-radius:5px;color:#5a7180;background:#f7fafb}
.score-strip{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--line);border-radius:10px;margin:15px 0 18px;background:#f9fbfc}.score{padding:13px 15px;border-right:1px solid var(--line)}.score:last-child{border:0}.score b{display:block;font-size:24px;line-height:1.2;letter-spacing:-1px}.score small{font-size:10px;color:#718592}.empty-state{text-align:center;padding:35px 15px 30px}.empty-icon{width:55px;height:55px;display:grid;place-items:center;background:#f0f5f8;border:1px solid #dce6ec;border-radius:50%;margin:auto auto 14px;color:#698293;font-size:24px}.empty-state strong{font-size:15px}.empty-state p{color:#7d8d98;font-size:12px;max-width:300px;margin:8px auto}
.action-row{display:flex;gap:12px;padding:14px 0;border-bottom:1px solid #eaf0f3}.action-number{width:25px;height:25px;flex-shrink:0;display:grid;place-items:center;font-size:10px;background:#eef4f7;border-radius:7px;color:#698192}.action-main{flex:1;min-width:0}.action-head{display:flex;justify-content:space-between;gap:10px;align-items:center}.action-head strong{font-size:12px}.action-target{font-size:12px;color:#40596c;margin-top:4px;overflow-wrap:anywhere}.action-reason{font-size:10px;color:#82929e;margin-top:4px}.answer-label{font-size:10px;font-weight:750;letter-spacing:1.3px;color:#00796c;margin:20px 0 7px}.answer-box{font-size:14px;line-height:1.8;white-space:pre-wrap;overflow-wrap:anywhere;color:#294254;padding:16px;background:#f2f8f6;border-radius:10px;max-height:360px;overflow:auto}.footer{font-size:10px;color:#8796a1;display:flex;justify-content:space-between;border-top:1px solid #dce5eb;padding-top:15px;margin-top:25px}.mail-head{padding:12px;background:#f5f8fa;border-radius:8px;font-size:12px;line-height:1.8}
@media(max-width:850px){.block-container{padding:1rem}.flow{padding:12px;gap:5px}.flow small{display:none}.step-num{display:none}.hero h1{font-size:25px!important}.brandbar{flex-wrap:wrap}}
</style>''',unsafe_allow_html=True)
