"""
app.py - Streamlit Frontend for Sports Lot Optimiser.

Dashboard for turf managers and interactive player booking flow:
- 5 Tabs:
    1. Court Schedule
    2. Fill Empty Slot (Main Demo & WhatsApp Generator)
    3. Player Booking Page (Interactive Checkout Screen)
    4. Booking History
    5. Revenue & Results
"""

import streamlit as st
import pandas as pd
import altair as alt
import integration
from outreach import generate_outreach

# =============================================================================
# Page Setup & Styling
# =============================================================================
st.set_page_config(
    page_title="Turf Slot Optimiser | Smart Booking Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern sports-tech polish
st.markdown(
    """
    <style>
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #1A1F2C;
        border: 1px solid #2B3245;
        border-radius: 10px;
        padding: 12px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem;
        color: #94A3B8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.65rem;
        color: #FFFFFF;
        font-weight: 700;
    }

    /* Decision Badges */
    .badge-large-discount {
        background-color: #D97706;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.88rem;
        display: inline-block;
    }
    .badge-small-discount {
        background-color: #0284C7;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.88rem;
        display: inline-block;
    }
    .badge-notify-only {
        background-color: #7C3AED;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.88rem;
        display: inline-block;
    }
    .badge-no-action {
        background-color: #059669;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.88rem;
        display: inline-block;
    }

    /* WhatsApp Preview Card */
    .whatsapp-card {
        background-color: #0B141A;
        border: 1px solid #1F2C34;
        border-left: 4px solid #25D366;
        border-radius: 8px;
        padding: 16px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #E9EDEF;
        white-space: pre-wrap;
        line-height: 1.5;
        font-size: 0.95rem;
    }

    /* Customer Mobile Checkout Card */
    .checkout-browser-bar {
        background-color: #1A2233;
        border: 1px solid #2F3B52;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        padding: 8px 16px;
        font-family: monospace;
        font-size: 0.85rem;
        color: #60A5FA;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .checkout-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-bottom-left-radius: 10px;
        border-bottom-right-radius: 10px;
        padding: 24px;
        margin-bottom: 20px;
    }
    .pass-card {
        background: linear-gradient(135deg, #064E3B 0%, #0F172A 100%);
        border: 1px solid #059669;
        border-radius: 12px;
        padding: 20px;
        color: #ECFDF5;
        margin-top: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# Session State Initialization & Navigation Helper
# =============================================================================
if "selected_slot_id" not in st.session_state:
    st.session_state["selected_slot_id"] = "S101-DEMO"

if "checkout_slot_id" not in st.session_state:
    st.session_state["checkout_slot_id"] = "S101-DEMO"

if "last_evaluation" not in st.session_state:
    st.session_state["last_evaluation"] = None

if "last_outreach" not in st.session_state:
    st.session_state["last_outreach"] = None

def set_active_tab(tab_name: str, slot_id: str | None = None):
    """Programmatically switches active tab and synchronizes slot state."""
    st.session_state["active_tab"] = tab_name
    if slot_id:
        st.session_state["selected_slot_id"] = slot_id
        st.session_state["tab2_slot_selector"] = slot_id
        st.session_state["checkout_slot_id"] = slot_id
        st.session_state["last_evaluation"] = None
        st.session_state["last_outreach"] = None

# =============================================================================
# Sidebar: Control Panel & Demo Switcher
# =============================================================================
with st.sidebar:
    st.title("Turf Slot Optimiser")
    st.caption("Smart Court Booking & Pricing Assistant")
    
    st.markdown("---")
    st.subheader("Quick Demo Examples")

    slot_to_example_idx = {
        "S101-DEMO": 0,
        "S102-DEMO": 1,
        "S103-DEMO": 2,
    }
    active_slot_now = st.session_state.get("selected_slot_id", "S101-DEMO")
    current_example_idx = slot_to_example_idx.get(active_slot_now, 3)

    example_options = [
        "Example 1: Quiet Afternoon (20% Deal)",
        "Example 2: Average Demand (10% Deal)",
        "Example 3: Prime Weekend Evening (Keep Full Price)",
        "[Custom / Selected from Table]",
    ]

    def on_sidebar_demo_choice():
        choice = st.session_state.get("sidebar_demo_choice")
        if choice == "Example 1: Quiet Afternoon (20% Deal)":
            set_active_tab("2. Fill Empty Slot", "S101-DEMO")
        elif choice == "Example 2: Average Demand (10% Deal)":
            set_active_tab("2. Fill Empty Slot", "S102-DEMO")
        elif choice == "Example 3: Prime Weekend Evening (Keep Full Price)":
            set_active_tab("2. Fill Empty Slot", "S103-DEMO")

    st.selectbox(
        "Select an Example:",
        options=example_options,
        index=current_example_idx,
        key="sidebar_demo_choice",
        on_change=on_sidebar_demo_choice,
        help="Quickly test realistic court slots to see how pricing adjusts.",
    )

    st.markdown("---")
    st.subheader("Assistant Status")
    st.success("**System Online**\n\nReady to analyze courts and suggest smart prices.")

    def on_reset_demo_clicked():
        integration.reset_demo_data()
        set_active_tab("1. Court Schedule", "S101-DEMO")

    st.button("Reset Demo Data", on_click=on_reset_demo_clicked, use_container_width=True)


# Load latest data via integration interface
slots_df = integration.load_slots()
segments_df = integration.load_segments()
booking_log_df = integration.load_booking_log()

# =============================================================================
# Main Header
# =============================================================================
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("Turf Revenue & Slot Optimiser")
    st.markdown("Fill empty courts, protect profit margins, and notify the right players at the right time.")
with col_h2:
    vacant_count = len(slots_df[slots_df["status"] == "vacant"])
    booked_count = len(slots_df[slots_df["status"] == "booked"])
    st.metric("Overall Occupancy", f"{(booked_count / len(slots_df) * 100):.1f}%", f"{vacant_count} Available")

# =============================================================================
# Tabs Navigation (With direct programmatic navigation)
# =============================================================================
TAB_TITLES = [
    "1. Court Schedule",
    "2. Fill Empty Slot",
    "3. Booking History",
    "4. Revenue & Results",
]

if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = TAB_TITLES[0]

tab1, tab2, tab3, tab4 = st.tabs(TAB_TITLES, on_change="rerun", key="active_tab")

# =============================================================================
# TAB 1: Court Schedule
# =============================================================================
with tab1:
    st.subheader("Court Availability & Schedule")
    st.caption("Check which courts are open and their typical booking rates.")

    # High Level KPI Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    total_slots = len(slots_df)
    vacant_slots = len(slots_df[slots_df["status"] == "vacant"])
    rev_at_risk = slots_df[slots_df["status"] == "vacant"]["base_price"].sum()
    avg_fill = slots_df["historical_fill_rate"].mean() * 100

    kpi1.metric("Total Court Slots", f"{total_slots}")
    kpi2.metric("Available Slots", f"{vacant_slots}", delta=f"{vacant_slots} Unbooked", delta_color="inverse")
    kpi3.metric("Potential Unsold Revenue", f"₹{rev_at_risk:,.0f}", help="Total standard revenue from currently unbooked slots")
    kpi4.metric("Average Booking Rate", f"{avg_fill:.1f}%")

    st.markdown("---")

    # Filters Row
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    turfs = ["All Venues"] + sorted(slots_df["turf_name"].unique().tolist())
    selected_turf = f_col1.selectbox("Filter by Venue:", turfs)

    sports = ["All Sports"] + sorted(slots_df["sport"].unique().tolist())
    selected_sport = f_col2.selectbox("Filter by Sport:", sports)

    status_opts = ["All Statuses", "vacant", "booked"]
    selected_status = f_col3.selectbox("Filter by Status:", status_opts)

    days = ["All Days"] + sorted(slots_df["day_of_week"].unique().tolist())
    selected_day = f_col4.selectbox("Filter by Day:", days)

    # Apply Filters
    filtered_df = slots_df.copy()
    if selected_turf != "All Venues":
        filtered_df = filtered_df[filtered_df["turf_name"] == selected_turf]
    if selected_sport != "All Sports":
        filtered_df = filtered_df[filtered_df["sport"] == selected_sport]
    if selected_status != "All Statuses":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]
    if selected_day != "All Days":
        filtered_df = filtered_df[filtered_df["day_of_week"] == selected_day]

    # Display Table with clean, non-technical column headers
    st.dataframe(
        filtered_df,
        column_config={
            "slot_id": st.column_config.TextColumn("Slot ID", width="small"),
            "turf_name": st.column_config.TextColumn("Venue", width="medium"),
            "sport": st.column_config.TextColumn("Sport", width="small"),
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "day_of_week": st.column_config.TextColumn("Day", width="small"),
            "time_slot": st.column_config.TextColumn("Time", width="small"),
            "lead_time_hrs": st.column_config.NumberColumn("Hours Left", format="%d hrs"),
            "base_price": st.column_config.NumberColumn("Standard Price", format="₹%d"),
            "cost_to_operate": st.column_config.NumberColumn("Operating Cost", format="₹%d"),
            "historical_fill_rate": st.column_config.ProgressColumn(
                "Usual Demand",
                format="%.0f%%",
                min_value=0.0,
                max_value=1.0,
            ),
            "status": st.column_config.TextColumn("Status", width="small"),
            "tags": st.column_config.TextColumn("Note", width="medium"),
        },
        width="stretch",
        hide_index=True,
    )

    # Quick Select Action
    st.markdown("#### Quick Action: Send to Pricing Assistant")
    vacant_ids = slots_df[slots_df["status"] == "vacant"]["slot_id"].tolist()
    if vacant_ids:
        q_col1, q_col2 = st.columns([3, 1])
        pick_slot = q_col1.selectbox("Select an available court slot to review in Tab 2:", vacant_ids)
        q_col2.button(
            "Review Slot in Tab 2",
            key="tab1_review_slot_btn",
            on_click=set_active_tab,
            args=("2. Fill Empty Slot", pick_slot),
            use_container_width=True,
        )


# =============================================================================
# TAB 2: Fill Empty Slot (Main Demo & Outreach Generator)
# =============================================================================
with tab2:
    st.subheader("Smart Slot Assistant")
    st.caption("Pick an available court, see the recommended pricing, and preview the message to send players.")

    # Slot Selector Bar
    all_slot_ids = slots_df["slot_id"].tolist()
    curr_selected = st.session_state.get("selected_slot_id", all_slot_ids[0])
    if curr_selected not in all_slot_ids:
        curr_selected = all_slot_ids[0]
        st.session_state["selected_slot_id"] = curr_selected

    default_idx = all_slot_ids.index(curr_selected)

    def on_tab2_slot_change():
        chosen = st.session_state.get("tab2_slot_selector")
        if chosen:
            st.session_state["selected_slot_id"] = chosen
            st.session_state["checkout_slot_id"] = chosen
            st.session_state["last_evaluation"] = None
            st.session_state["last_outreach"] = None

    sel_col1, sel_col2 = st.columns([3, 1])
    active_slot_id = sel_col1.selectbox(
        "Select Court Slot:",
        options=all_slot_ids,
        index=default_idx,
        key="tab2_slot_selector",
        on_change=on_tab2_slot_change,
        format_func=lambda s_id: f"{s_id} | {slots_df.loc[slots_df['slot_id']==s_id, 'turf_name'].values[0]} | {slots_df.loc[slots_df['slot_id']==s_id, 'sport'].values[0]} ({slots_df.loc[slots_df['slot_id']==s_id, 'time_slot'].values[0]}) - {slots_df.loc[slots_df['slot_id']==s_id, 'status'].values[0].upper()}",
    )
    # Ensure active_slot_id is up-to-date with session_state
    active_slot_id = st.session_state.get("selected_slot_id", active_slot_id)
    slot_match = slots_df[slots_df["slot_id"] == active_slot_id]
    if slot_match.empty:
        slot_record = slots_df.iloc[0].to_dict()
    else:
        slot_record = slot_match.iloc[0].to_dict()

    # Slot Overview Card
    st.markdown("##### Slot Details")
    is_vacant = slot_record["status"].lower() == "vacant"
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Venue & Sport", f"{slot_record['sport']}", slot_record['turf_name'])
    c2.metric("Day & Time", f"{slot_record['time_slot']}", f"{slot_record['day_of_week']}")
    c3.metric("Hours Until Slot", f"{slot_record['lead_time_hrs']} hrs left")
    c4.metric("Standard Price / Cost", f"₹{slot_record['base_price']:.0f}", f"Running Cost: ₹{slot_record['cost_to_operate']:.0f}")
    
    status_display = "🟢 VACANT" if is_vacant else "🔴 BOOKED"
    c5.metric("Court Status", status_display, f"Demand: {slot_record['historical_fill_rate'] * 100:.0f}%")

    margin_room = slot_record['base_price'] - slot_record['cost_to_operate']
    st.caption(f"**Profit Room:** ₹{margin_room:.0f} per booking (Standard price ₹{slot_record['base_price']:.0f} minus ₹{slot_record['cost_to_operate']:.0f} running cost) | **Historical Demand:** {slot_record['historical_fill_rate'] * 100:.0f}% average fill rate")

    st.markdown("---")

    # Run Agent Button
    run_col, info_col = st.columns([1, 2])
    with run_col:
        btn_label = "Check Best Price & Offer" if is_vacant else "Review Slot Details"
        run_clicked = st.button(btn_label, type="primary", use_container_width=True)

    with info_col:
        if not is_vacant:
            st.warning("This court slot is currently marked as **BOOKED**.")

    if run_clicked:
        with st.spinner("Finding the best price and message for players..."):
            # Inside the 'Run Agent' button callback (Person C contract):
            selected_slot = slot_record
            decision_result = integration.evaluate_slot(selected_slot)
            outreach_result = generate_outreach(selected_slot, decision_result, segments_df)

            matched_segment = outreach_result["matched_segment"]
            rendered_message = outreach_result["message"]

            st.session_state["last_evaluation"] = decision_result
            st.session_state["last_outreach"] = outreach_result
            st.toast(f"Recommendation ready for {slot_record['slot_id']}.")

    # Render Results if evaluation exists
    if st.session_state["last_evaluation"] is not None:
        eval_data = st.session_state["last_evaluation"]
        outreach_data = st.session_state["last_outreach"]
        decision = eval_data.get("decision", "no_action")
        discount_pct = eval_data.get("discount_pct", 0.0)

        st.markdown("### Recommendation & Price Breakdown")

        # Visual Decision Banner
        res_col1, res_col2, res_col3, res_col4 = st.columns(4)

        with res_col1:
            st.markdown("**Suggested Action:**")
            if decision == "notify_large_discount":
                st.markdown("<span class='badge-large-discount'>SPECIAL OFFER (20% OFF)</span>", unsafe_allow_html=True)
            elif decision == "notify_small_discount":
                st.markdown("<span class='badge-small-discount'>QUICK DEAL (10% OFF)</span>", unsafe_allow_html=True)
            elif decision == "notify_only":
                st.markdown("<span class='badge-notify-only'>NOTIFY PLAYERS (FULL PRICE)</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='badge-no-action'>KEEP FULL PRICE</span>", unsafe_allow_html=True)

        with res_col2:
            discount_label = f"{discount_pct:.0f}% OFF" if discount_pct > 0 else "Full Price (No Discount)"
            st.metric("Recommended Offer", discount_label)

        with res_col3:
            effective_price = slot_record["base_price"] * (1.0 - (discount_pct / 100.0))
            st.metric("New Booking Price", f"₹{effective_price:.0f}", f"Standard: ₹{slot_record['base_price']:.0f}")

        with res_col4:
            net_contrib = effective_price - slot_record["cost_to_operate"]
            margin_saved = (slot_record["base_price"] - slot_record["cost_to_operate"]) if decision == "no_action" else 0.0
            if decision == "no_action":
                st.metric("Profit Protected", f"₹{margin_saved:.0f}", "Saved from Unnecessary Discount")
            else:
                st.metric("Profit Per Booking", f"₹{net_contrib:.0f}", f"Covers ₹{slot_record['cost_to_operate']:.0f} Running Cost")

        st.caption("**Recommendation Status:** Verified and Ready")

        # Reasoning Bullets
        st.markdown("##### Why This Decision Makes Sense:")
        reasoning_list = eval_data.get("reasoning", [])
        for r in reasoning_list:
            st.markdown(f"- {r}")

        st.markdown("---")

        # Outreach & Target Customer Segment Section
        matched_segment = outreach_data["matched_segment"]
        rendered_message = outreach_data["message"]

        # Display in Streamlit (Contract from Person C):
        st.subheader(f"🎯 Target Audience: {matched_segment}")
        st.markdown(rendered_message)

        st.markdown("---")


        # Booking Action Section
        st.markdown("### Confirm Booking")
        st.markdown("Once confirmed, this court is marked as booked and recorded in the booking history.")

        b_col1, b_col2 = st.columns([1, 2])
        with b_col1:
            book_enabled = slot_record["status"].lower() == "vacant"
            if st.button("Confirm Booking", type="primary", disabled=not book_enabled, use_container_width=True):
                success, msg = integration.book_slot(
                    active_slot_id,
                    eval_data,
                    segment_notified=outreach_data.get("matched_segment", "Direct"),
                )
                if success:
                    st.success(f"Confirmed! Court {active_slot_id} is now booked.")
                    st.rerun()
                else:
                    st.error(msg)
        with b_col2:
            if not book_enabled:
                st.info("This court slot is already **BOOKED**.")
                st.button(
                    "View in Booking History",
                    key="tab2_to_history_btn",
                    on_click=set_active_tab,
                    args=("3. Booking History",),
                    use_container_width=True,
                )
            else:
                st.caption("Clicking 'Confirm Booking' reserves the court, updates the schedule, and adds a record to the booking history.")

# =============================================================================
# TAB 3: Booking History
# =============================================================================
with tab3:
    st.subheader("Booking & Message History")
    st.caption("Complete history of past recommendations, player messages, and confirmed bookings.")

    # Filter by decision
    log_decisions = ["All Actions"] + sorted(booking_log_df["decision"].unique().tolist())
    log_filt_col, log_count_col = st.columns([3, 1])
    selected_log_decision = log_filt_col.selectbox("Filter History by Action:", log_decisions)
    log_count_col.metric("Total Records", f"{len(booking_log_df)}")

    filtered_log = booking_log_df.copy()
    if selected_log_decision != "All Actions":
        filtered_log = filtered_log[filtered_log["decision"] == selected_log_decision]

    st.dataframe(
        filtered_log,
        column_config={
            "slot_id": st.column_config.TextColumn("Slot ID", width="small"),
            "decision": st.column_config.TextColumn("Action Taken", width="medium"),
            "discount_pct": st.column_config.NumberColumn("Discount Given", format="%.0f%%"),
            "reasoning": st.column_config.TextColumn("Reason", width="large"),
            "segment_notified": st.column_config.TextColumn("Target Players", width="medium"),
            "source": st.column_config.TextColumn("Type", width="small"),
            "timestamp": st.column_config.TextColumn("Date & Time", width="medium"),
        },
        width="stretch",
        hide_index=True,
    )

    # Download CSV
    csv_data = filtered_log.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download History as CSV",
        data=csv_data,
        file_name="booking_history.csv",
        mime="text/csv",
    )

# =============================================================================
# TAB 4: Revenue & Results
# =============================================================================
with tab4:
    st.subheader("Business Results & Revenue Impact")
    st.caption("See how smart pricing fills quiet afternoon courts without losing money on busy weekend slots.")

    # High-level business metrics
    a1, a2, a3, a4 = st.columns(4)
    total_processed = len(booking_log_df)
    discounts_given = len(booking_log_df[booking_log_df["discount_pct"] > 0])
    avg_discount = booking_log_df[booking_log_df["discount_pct"] > 0]["discount_pct"].mean() if discounts_given > 0 else 0.0
    no_actions = len(booking_log_df[booking_log_df["decision"] == "no_action"])

    a1.metric("Slots Reviewed", f"{total_processed}")
    a2.metric("Slots Saved With Offers", f"{discounts_given}", help="Quiet slots booked after offering a small discount")
    a3.metric("Average Discount Given", f"{avg_discount:.1f}%")
    a4.metric("Full-Price Slots Preserved", f"{no_actions}", help="Busy slots kept at full price to protect profit")

    st.markdown("---")

    # Chart 1: Visualizing the Weekday Afternoon Slump (The Business Problem)
    st.markdown("##### Court Demand Throughout the Week")
    st.caption("Notice how weekday afternoons (12:00 - 17:00) are quiet, while evenings and weekends fill up naturally.")

    chart_data = slots_df.copy()
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    chart = (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("day_of_week:N", sort=day_order, title="Day of Week"),
            y=alt.Y("mean(historical_fill_rate):Q", title="Average Booking Rate", axis=alt.Axis(format="%")),
            color=alt.Color(
                "mean(historical_fill_rate):Q",
                scale=alt.Scale(scheme="tealblues"),
                legend=alt.Legend(title="Demand Rate"),
            ),
            tooltip=[
                alt.Tooltip("day_of_week:N", title="Day"),
                alt.Tooltip("mean(historical_fill_rate):Q", title="Avg Booking Rate", format=".0%"),
            ],
        )
        .properties(height=320)
    )

    st.altair_chart(chart, width="stretch")

    # Chart 2: Decisions Breakdown
    st.markdown("##### Pricing Strategy Breakdown")
    decision_counts = booking_log_df["decision"].value_counts().reset_index()
    decision_counts.columns = ["Action", "Count"]

    dec_chart = (
        alt.Chart(decision_counts)
        .mark_bar(color="#00D47E")
        .encode(
            x=alt.X("Action:N", sort="-y", title="Action"),
            y=alt.Y("Count:Q", title="Number of Courts"),
            tooltip=["Action", "Count"],
        )
        .properties(height=260)
    )
    st.altair_chart(dec_chart, width="stretch")

    st.markdown("---")
    st.markdown("##### Key Business Takeaway:")
    st.info(
        "**• Why not discount every slot?**\n"
        "Slashing prices on weekend evenings wastes money because players are already happy to book at full price.\n\n"
        "**• How smart pricing wins:**\n"
        "It offers deals only on quiet weekday afternoon courts to attract players who otherwise wouldn't come, while protecting full prices on popular evening slots."
    )
