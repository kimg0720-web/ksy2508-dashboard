#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

#######################
# Page configuration
st.set_page_config(
    page_title="US Population Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("default")

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)


#######################
# Load data
df_reshaped = pd.read_csv('국가유산청_발굴보고서.csv', encoding = "cp949") ## 분석 데이터 넣기


#######################
# Sidebar
with st.sidebar:
    st.markdown("## 국가유산 발굴보고서 대시보드")
    st.caption("필터를 변경하면 전체 차트가 동기화되도록 설계")

    df = df_reshaped.copy()

    # ---- 파생 컬럼 준비(있을 때만) ----
    # 제출연도
    if "제출일" in df.columns:
        df["제출일"] = pd.to_datetime(df["제출일"], errors="coerce")
        df["제출연도"] = df["제출일"].dt.year

    # 위젯 배치용 컨테이너
    st.write("### 필터")

    # 1) 연도(단일/범위 자동)
    year_range = None
    if "제출연도" in df.columns and df["제출연도"].notna().any():
        y_min = int(df["제출연도"].min())
        y_max = int(df["제출연도"].max())
        year_range = st.slider(
            "연도 범위",
            min_value=y_min,
            max_value=y_max,
            value=(y_min, y_max),
            step=1,
            help="제출연도 기준으로 데이터 범위를 제한"
        )

    # 2) 지역(시도 → 시군구 드릴다운)
    selected_sido = None
    selected_sigungu = None

    if "조사시도" in df.columns and df["조사시도"].notna().any():
        sido_options = sorted(df["조사시도"].dropna().unique().tolist())
        selected_sido = st.multiselect(
            "시도 선택",
            options=sido_options,
            default=sido_options,
            help="선택한 시도만 분석"
        )

        if "조사시군구" in df.columns and df["조사시군구"].notna().any():
            _df_sido = df[df["조사시도"].isin(selected_sido)] if selected_sido else df
            sigungu_options = sorted(_df_sido["조사시군구"].fillna("미상").unique().tolist())
            selected_sigungu = st.multiselect(
                "시군구 선택",
                options=sigungu_options,
                default=sigungu_options,
                help="시군구 단위로 세분화"
            )

    # 3) 시대
    selected_era = None
    if "시대" in df.columns and df["시대"].notna().any():
        era_options = sorted(df["시대"].fillna("미상").unique().tolist())
        selected_era = st.multiselect(
            "시대",
            options=era_options,
            default=era_options
        )

    # 4) 유적성격
    selected_type = None
    if "유적성격" in df.columns and df["유적성격"].notna().any():
        type_options = sorted(df["유적성격"].fillna("미상").unique().tolist())
        selected_type = st.multiselect(
            "유적성격",
            options=type_options,
            default=type_options
        )

    # 5) 발간기관
    selected_org = None
    if "발간기관" in df.columns and df["발간기관"].notna().any():
        org_options = sorted(df["발간기관"].fillna("미상").unique().tolist())
        selected_org = st.multiselect(
            "발간기관",
            options=org_options,
            default=None,
            help="선택 시 해당 기관만 표시(미선택=전체)"
        )

    # 6) 조사면적 범위 (상위 99% 캡)
    area_range = None
    if "조사면적" in df.columns and df["조사면적"].notna().any():
        q01 = float(max(0, df["조사면적"].quantile(0.01)))
        q99 = float(df["조사면적"].quantile(0.99))
        min_area = int(q01)
        max_area = int(q99)
        area_range = st.slider(
            "조사면적(㎡) 범위",
            min_value=min_area,
            max_value=max_area,
            value=(min_area, max_area),
            step=max(1, (max_area - min_area) // 100),
            help="극단값 영향을 줄이기 위해 1–99 분위로 기본 제한"
        )

    # 7) 키워드 검색(보고서명/유적사업명)
    keyword = st.text_input(
        "키워드 검색",
        value="",
        placeholder="보고서명 또는 유적사업명에서 검색"
    )

    # 8) 테마 선택(표시용 상태값)
    theme = st.radio(
        "대시보드 테마",
        options=["Dark", "Light"],
        index=0,
        horizontal=True
    )
    st.session_state["theme_pref"] = theme

    # ---- 필터 적용 로직(사이드바에서 미리 계산하여 세션에 저장) ----
    filtered = df.copy()

    if year_range and "제출연도" in filtered.columns:
        filtered = filtered[(filtered["제출연도"] >= year_range[0]) & (filtered["제출연도"] <= year_range[1])]

    if selected_sido is not None and len(selected_sido) > 0 and "조사시도" in filtered.columns:
        filtered = filtered[filtered["조사시도"].isin(selected_sido)]

    if selected_sigungu is not None and len(selected_sigungu) > 0 and "조사시군구" in filtered.columns:
        filtered = filtered[filtered["조사시군구"].fillna("미상").isin(selected_sigungu)]

    if selected_era is not None and len(selected_era) > 0 and "시대" in filtered.columns:
        filtered = filtered[filtered["시대"].fillna("미상").isin(selected_era)]

    if selected_type is not None and len(selected_type) > 0 and "유적성격" in filtered.columns:
        filtered = filtered[filtered["유적성격"].fillna("미상").isin(selected_type)]

    if selected_org is not None and len(selected_org) > 0 and "발간기관" in filtered.columns:
        filtered = filtered[filtered["발간기관"].fillna("미상").isin(selected_org)]

    if area_range and "조사면적" in filtered.columns:
        filtered = filtered[filtered["조사면적"].between(area_range[0], area_range[1], inclusive="both")]

    if keyword:
        mask = pd.Series([True] * len(filtered))
        cols_for_kw = [c for c in ["보고서명", "유적사업명"] if c in filtered.columns]
        if cols_for_kw:
            kw = keyword.strip().lower()
            mask = False
            for c in cols_for_kw:
                mask = mask | filtered[c].astype(str).str.lower().str.contains(kw, na=False)
            filtered = filtered[mask]

    # 세션에 저장 → 본문(메인 패널)에서 사용
    st.session_state["filtered_df"] = filtered

    # 다운로드(현재 필터 결과)
    st.download_button(
        "현재 필터 결과 다운로드 (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name="filtered_excavation_reports.csv",
        mime="text/csv",
        use_container_width=True
    )

    # 요약 뱃지
    st.success(f"현재 조건에 해당하는 보고서: **{len(filtered):,}건**")


#######################
# Plots



#######################
# Dashboard Main Panel
col = st.columns((1.5, 4.5, 2), gap='medium')

with col[0]:
    st.markdown("### 📊 요약 KPI")

    # 필터된 DF (없으면 원본)
    df = st.session_state.get("filtered_df", df_reshaped).copy()

    # 제출연도 파생 (사이드바에서 못 만든 경우 대비)
    if "제출연도" not in df.columns and "제출일" in df.columns:
        df["제출일"] = pd.to_datetime(df["제출일"], errors="coerce")
        df["제출연도"] = df["제출일"].dt.year

    # --- KPI 3종 ---
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("보고서 수", f"{len(df):,}")

    with k2:
        if "조사면적" in df.columns and df["조사면적"].notna().any():
            st.metric("총 조사면적 (㎡)", f"{df['조사면적'].sum():,.0f}")
        else:
            st.metric("총 조사면적 (㎡)", "데이터 없음")

    with k3:
        if "조사면적" in df.columns and df["조사면적"].notna().any():
            st.metric("건당 평균면적 (㎡)", f"{df['조사면적'].mean():,.0f}")
        else:
            st.metric("건당 평균면적 (㎡)", "데이터 없음")

    # 최근연도 vs 전년 보고서 수 비교(가능할 때만)
    if "제출연도" in df.columns and df["제출연도"].notna().any():
        latest_year = int(df["제출연도"].max())
        prev_year = latest_year - 1
        cnt_latest = int((df["제출연도"] == latest_year).sum())
        cnt_prev = int((df["제출연도"] == prev_year).sum())
        if cnt_prev > 0:
            delta = round((cnt_latest - cnt_prev) / cnt_prev * 100, 1)
            st.caption(f"최근연도({latest_year}) 보고서 {cnt_latest:,}건 · 전년({prev_year}) 대비 {delta:+.1f}%")
        else:
            st.caption(f"최근연도({latest_year}) 보고서 {cnt_latest:,}건")

    st.markdown("---")

    # --- 도넛 차트: 시대 / 유적성격 ---
    p1, p2 = st.columns(2)

    # 시대 분포
    with p1:
        if "시대" in df.columns and df["시대"].notna().any():
            era_counts = df["시대"].fillna("미상").value_counts().reset_index()
            era_counts.columns = ["시대", "건수"]
            fig_era = px.pie(
                era_counts,
                names="시대",
                values="건수",
                hole=0.55,
                title="시대 분포"
            )
            fig_era.update_layout(
                margin=dict(l=0, r=0, t=40, b=0),
                height=300,
                showlegend=True
            )
            st.plotly_chart(fig_era, use_container_width=True)
        else:
            st.info("시대 정보가 없습니다.")

    # 유적성격 분포 (Top 6 + 기타)
    with p2:
        if "유적성격" in df.columns and df["유적성격"].notna().any():
            type_counts = df["유적성격"].fillna("미상").value_counts().reset_index()
            type_counts.columns = ["유적성격", "건수"]
            top_n = 6
            if len(type_counts) > top_n:
                top = type_counts.iloc[:top_n].copy()
                other_sum = int(type_counts.iloc[top_n:]["건수"].sum())
                top.loc[len(top)] = ["기타", other_sum]
                type_counts = top

            fig_type = px.pie(
                type_counts,
                names="유적성격",
                values="건수",
                hole=0.55,
                title="유적성격 분포"
            )
            fig_type.update_layout(
                margin=dict(l=0, r=0, t=40, b=0),
                height=300,
                showlegend=True
            )
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("유적성격 정보가 없습니다.")

    # --- 데이터 품질 알림 ---
    notes = []
    if "조사면적" in df.columns:
        notes.append(f"조사면적 결측 {df['조사면적'].isna().sum():,}건")
    if "조사기간" in df.columns:
        notes.append(f"조사기간 결측 {df['조사기간'].isna().sum():,}건")
    if notes:
        st.warning("데이터 품질: " + " · ".join(notes))


with col[1]:
    st.markdown("### 🗺️ 메인 시각화")

    # 필터된 DF (없으면 원본)
    df = st.session_state.get("filtered_df", df_reshaped).copy()

    # 날짜 파생
    if "제출연도" not in df.columns and "제출일" in df.columns:
        df["제출일"] = pd.to_datetime(df["제출일"], errors="coerce")
        df["제출연도"] = df["제출일"].dt.year
    if "제출월" not in df.columns:
        if "제출일" in df.columns:
            df["제출월"] = pd.to_datetime(df["제출일"], errors="coerce").dt.month

    # -----------------------------
    # (1) 지역 분포
    # -----------------------------
    st.markdown("#### (1) 지역 분포")
    tab_sido, tab_sigungu = st.tabs(["시도 분포", "시군구 Top 15"])

    # 1-1) 시도 분포(Choropleth or Bar fallback)
    with tab_sido:
        if "조사시도" in df.columns and df["조사시도"].notna().any():
            sido_agg = (
                df.groupby("조사시도", dropna=True)
                  .agg(건수=("조사시도", "size"),
                       합계면적=("조사면적", "sum"))
                  .reset_index()
            )
            metric = st.radio("색상 기준", options=["건수", "합계면적"], index=0, horizontal=True, key="metric_sido")

            geojson = None
            try:
                import os, json
                for candidate in ["korea_sido.geojson", "data/korea_sido.geojson", "/mnt/data/korea_sido.geojson"]:
                    if os.path.exists(candidate):
                        with open(candidate, "r", encoding="utf-8") as f:
                            geojson = json.load(f)
                        break
            except Exception:
                geojson = None

            if geojson is not None:
                # GeoJSON의 시도 이름 키가 환경마다 다를 수 있어 후보 키를 순차 시도
                fid_keys = ["properties.SIG_KOR_NM", "properties.CTP_KOR_NM", "properties.name"]
                used_key = None
                for k in fid_keys:
                    # 간단 검증: 첫 피처에서 키가 존재하면 사용
                    try:
                        _ = geojson["features"][0]
                        # 중첩 키 처리
                        d = geojson["features"][0]
                        for kk in k.split("."):
                            d = d[kk]
                        used_key = k
                        break
                    except Exception:
                        continue

                fig_map = px.choropleth(
                    sido_agg,
                    geojson=geojson,
                    featureidkey=used_key if used_key else "properties.name",
                    locations="조사시도",
                    color=metric,
                    hover_name="조사시도",
                    hover_data={"건수": True, "합계면적": ":,.0f"},
                )
                fig_map.update_geos(fitbounds="locations", visible=False)
                fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=420)
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.info("행정구역 GeoJSON 파일을 찾지 못해 막대그래프로 대체합니다.")
                order = sido_agg.sort_values(metric, ascending=False)
                fig_bar = px.bar(
                    order.head(17),
                    x="조사시도", y=metric,
                    hover_data=["건수", "합계면적"],
                    title=None
                )
                fig_bar.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=420, xaxis_tickangle=-30)
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("지역(조사시도) 정보가 없습니다.")

    # 1-2) 시군구 Top 15
    with tab_sigungu:
        if all(c in df.columns for c in ["조사시도", "조사시군구"]) and df["조사시군구"].notna().any():
            by_sigungu = (
                df.assign(조사시군구=df["조사시군구"].fillna("미상"))
                  .groupby(["조사시도", "조사시군구"], dropna=False)
                  .agg(건수=("조사시군구", "size"),
                       합계면적=("조사면적", "sum"))
                  .reset_index()
            )
            metric2 = st.radio("정렬 기준", options=["건수", "합계면적"], index=0, horizontal=True, key="metric_sigungu")
            topN = st.slider("표시 개수", min_value=5, max_value=30, value=15, step=1, key="sigungu_topN")
            top = by_sigungu.sort_values(metric2, ascending=False).head(topN).copy()
            top["라벨"] = top["조사시도"] + " " + top["조사시군구"]
            fig_rank = px.bar(
                top.sort_values(metric2, ascending=True),
                x=metric2, y="라벨", orientation="h",
                hover_data=["건수", "합계면적"],
                title=None
            )
            fig_rank.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=420)
            st.plotly_chart(fig_rank, use_container_width=True)
        else:
            st.info("시군구 정보가 없습니다.")

    st.markdown("---")

    # -----------------------------
    # (2) 연-월 타임 히트맵
    # -----------------------------
    st.markdown("#### (2) 연-월 타임 히트맵")
    if "제출연도" in df.columns and "제출월" in df.columns and df[["제출연도", "제출월"]].notna().all(axis=None):
        pivot = (
            df.pivot_table(index="제출연도", columns="제출월",
                           values=("보고서명" if "보고서명" in df.columns else df.columns[0]),
                           aggfunc="count", fill_value=0)
              .sort_index()
        )

        # 1~12월 컬럼 보장
        for m in range(1, 13):
            if m not in pivot.columns:
                pivot[m] = 0
        pivot = pivot[sorted(pivot.columns)]

        fig_heat = px.imshow(
            pivot.values,
            labels=dict(x="월", y="연도", color="건수"),
            x=[f"{m}월" for m in pivot.columns],
            y=[str(y) for y in pivot.index],
            text_auto=True,
            aspect="auto"
        )
        fig_heat.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=400)
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("연도/월 정보가 부족하여 히트맵을 생성할 수 없습니다.")

    st.markdown("---")

    # -----------------------------
    # (3) 요약 테이블
    # -----------------------------
    st.markdown("#### (3) 요약 테이블")
    base_cols = [c for c in ["보고서명", "제출일", "제출연도", "조사시도", "조사시군구", "조사면적", "시대", "유적성격", "발간기관"] if c in df.columns]
    if base_cols:
        if "제출일" in df.columns:
            show_df = df[base_cols].sort_values("제출일")
        else:
            show_df = df[base_cols]
        st.dataframe(show_df, use_container_width=True, height=350)
    else:
        st.info("요약 테이블에 표시할 핵심 컬럼이 없습니다.")



with col[2]:
    st.markdown("### 🏆 랭킹 & 인사이트")

    # 필터된 DF (없으면 원본)
    df = st.session_state.get("filtered_df", df_reshaped).copy()

    # 날짜 파생
    if "제출일" in df.columns:
        df["제출일"] = pd.to_datetime(df["제출일"], errors="coerce")
        if "제출연도" not in df.columns:
            df["제출연도"] = df["제출일"].dt.year

    # -----------------------------
    # 탭: 랭킹 / 인사이트 / About
    # -----------------------------
    tab_rank, tab_insight, tab_about = st.tabs(["랭킹", "인사이트", "About"])

    # =============================
    # (A) 랭킹
    # =============================
    with tab_rank:
        sub1, sub2, sub3 = st.tabs(["Top 시도", "Top 발간기관", "면적 상위 보고서"])

        # Top 시도
        with sub1:
            if "조사시도" in df.columns and df["조사시도"].notna().any():
                agg = df.groupby("조사시도", dropna=True).agg(건수=("조사시도", "size"))
                if "조사면적" in df.columns:
                    agg["합계면적"] = df.groupby("조사시도")["조사면적"].sum()
                agg = agg.reset_index()

                metric = st.radio(
                    "정렬 기준",
                    ["건수"] + (["합계면적"] if "합계면적" in agg.columns else []),
                    horizontal=True, index=0, key="rank_sido_metric"
                )
                topN = st.slider("표시 개수", 5, 20, 10, 1, key="rank_sido_topN")

                top = agg.sort_values(metric, ascending=False).head(topN)
                fig = px.bar(
                    top.sort_values(metric, ascending=True),
                    x=metric, y="조사시도", orientation="h",
                    hover_data=agg.columns.tolist(), title=None
                )
                fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("시도 정보가 없습니다.")

        # Top 발간기관
        with sub2:
            if "발간기관" in df.columns and df["발간기관"].notna().any():
                agg = df.groupby("발간기관", dropna=True).agg(건수=("발간기관", "size"))
                if "조사면적" in df.columns:
                    agg["합계면적"] = df.groupby("발간기관")["조사면적"].sum()
                agg = agg.reset_index()

                metric2 = st.radio(
                    "정렬 기준",
                    ["건수"] + (["합계면적"] if "합계면적" in agg.columns else []),
                    horizontal=True, index=0, key="rank_org_metric"
                )
                topN2 = st.slider("표시 개수", 5, 20, 10, 1, key="rank_org_topN")

                top2 = agg.sort_values(metric2, ascending=False).head(topN2)
                fig2 = px.bar(
                    top2.sort_values(metric2, ascending=True),
                    x=metric2, y="발간기관", orientation="h",
                    hover_data=agg.columns.tolist(), title=None
                )
                fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("발간기관 정보가 없습니다.")

        # 면적 상위 보고서
        with sub3:
            if "조사면적" in df.columns and "보고서명" in df.columns and df["조사면적"].notna().any():
                cols = ["보고서명", "조사면적", "조사시도", "조사시군구"]
                if "제출연도" in df.columns:
                    cols.append("제출연도")
                top_reports = df.sort_values("조사면적", ascending=False).head(10)[cols]

                fig3 = px.bar(
                    top_reports.sort_values("조사면적"),
                    x="조사면적", y="보고서명", orientation="h",
                    hover_data=[c for c in top_reports.columns if c != "조사면적"],
                    title=None
                )
                fig3.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350)
                st.plotly_chart(fig3, use_container_width=True)
                st.dataframe(top_reports, use_container_width=True, height=250)
            else:
                st.info("면적 또는 보고서명 정보가 부족합니다.")

    # =============================
    # (B) 인사이트
    # =============================
    with tab_insight:
        # 조사기간 → 조사_일수 계산(없으면 시도)
        if "조사_일수" not in df.columns and "조사기간" in df.columns:
            import re
            def _days(text):
                if pd.isna(text):
                    return None
                parts = re.split(r"[~\-–—to]+", str(text))
                if len(parts) < 2:
                    return None
                start = pd.to_datetime(parts[0].strip(), errors="coerce")
                end = pd.to_datetime(parts[1].strip(), errors="coerce")
                if pd.notna(start) and pd.notna(end) and end >= start:
                    return int((end - start).days) + 1
                return None
            df["조사_일수"] = df["조사기간"].map(_days)

        if "조사면적" in df.columns and "조사_일수" in df.columns and df[["조사면적", "조사_일수"]].notna().any().any():
            tmp = df[df["조사면적"].notna() & df["조사_일수"].notna()].copy()
            tmp = tmp[tmp["조사면적"] >= 0]

            size_hint = tmp["조사면적"].rank(pct=True)
            hover_cols = [c for c in ["보고서명", "조사시도", "조사시군구", "제출연도"] if c in tmp.columns]

            fig_scatter = px.scatter(
                tmp, x="조사_일수", y="조사면적",
                size=size_hint, size_max=18,
                hover_data=hover_cols,
                labels={"조사_일수": "조사 일수", "조사면적": "조사면적(㎡)"},
                title="조사면적 vs 조사 기간(일)"
            )
            fig_scatter.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=360)
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.caption("오른쪽 위로 갈수록 대형·장기 프로젝트일 가능성이 큼")
        else:
            st.info("조사기간을 일수로 변환할 수 없어 산점도를 표시하지 않습니다.")

    # =============================
    # (C) About
    # =============================
    with tab_about:
        with st.expander("About 이 대시보드", expanded=True):
            st.markdown(
                "- 데이터: 국가유산청 발굴보고서 제출 목록\n"
                "- 주요 지표 정의: 건수=보고서 수, 합계면적=조사면적 합, 평균면적=건당 평균\n"
                "- 전처리: 조사면적 결측·극단값은 시각화별로 제외될 수 있음\n"
                "- 팁: 사이드바 필터 변경 시 모든 차트가 동기화됩니다."
            )