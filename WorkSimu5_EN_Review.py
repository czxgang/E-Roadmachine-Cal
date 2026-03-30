import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Paver Simulation Calculator", layout="wide")

st.markdown("""
<style>
    /* 控制数字输入框容器的宽度 */
    div[data-testid="stNumberInput"] {
        width: 20% !important;  /* 可调百分比，相对于父容器 */
    }

     /* 侧边栏内的数字输入框，恢复为默认宽度（或指定宽度） */
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] {
        width: auto !important;   /* 自动适应，保留默认样式 */
    }
            
    /* 全局设置所有消息框宽度 */
    div[data-testid="stAlert"] {
        width:  fit-content !important;
    }
</style>
""", unsafe_allow_html=True)
st.title("ePaver Work Simu Calculator")


# ========== 1. 固定部件列表 ==========
FIXED_PARTS = pd.DataFrame({
    "Parts Name": [
        "Drive", "Conveyor", "Auger", "Screed",
        "Vibration", "Compaction", "HYD Cylinder", "Lv System"
    ],
    "Power(kW)": [30, 10, 16, 15, 8, 6.5, 10, 2]
})

# ========== 2. 自定义Load Factor计算函数 ==========
def my_usage_factor_calculator(part_names):
    factors = []
    for name in part_names:
        if "Cylinder" in name:
            factors.append(30 / (10 * 60))  # 0.05
        elif "Vibration" in name:
            factors.append(0)
        elif "Compaction" in name:
            factors.append(0.5)
        elif "Drive" in name:
            factors.append(0.2)
        elif "Auger" in name :
            factors.append(0.5)
        elif "Screed" in name:
            factors.append(0.0)
        elif "Lv System" in name:
            factors.append(0.5)
        else:
            factors.append(1.0)
    return factors

computed_factors = my_usage_factor_calculator(FIXED_PARTS["Parts Name"])
parts_df = FIXED_PARTS.copy()
parts_df["Load Factor"] = computed_factors

# ========== 侧边栏：部件参数 + 电池参数 ==========
with st.sidebar:
    st.header("Parts Spec")
    st.caption("Load Factor can be modified")
    st.dataframe(
        parts_df,
        use_container_width=True,
        column_config={
            "Parts Name": "Parts Name",
            "Power(kW)": st.column_config.NumberColumn("Power(kW)", format="%.1f"),
            "Load Factor": st.column_config.NumberColumn("Load Factor", format="%.2f")
        }
    )
    total_power_all = (parts_df["Power(kW)"] * parts_df["Load Factor"]).sum()
    st.metric("All parts average power", f"{total_power_all:.2f} kW")
    #st.caption("包含所有部件按Load Factor同时工作")

    st.divider()
    st.subheader("Battery Spec")
    dod_percent = st.number_input(
        "Battery available usage(%)", 
        min_value=10, max_value=100, value=95, step=5
    )
    dod = dod_percent / 100.0
    st.caption(f"Current ratio：{dod:.0%}")

# ========== 公共数据准备 ==========
df = parts_df.copy()
heater_mask = df["Parts Name"].str.contains("Screed", na=False)
has_heater = heater_mask.any()
if has_heater:
    heater_power = df.loc[heater_mask, "Power(kW)"].iloc[0]
else:
    heater_power = 0

if has_heater:
    normal_df = df[~heater_mask]
    total_power_normal = (normal_df["Power(kW)"] * normal_df["Load Factor"]).sum()
else:
    total_power_normal = total_power_all

heat_time = 0.5  # 小时

# ========== 主界面：三个标签页 ==========
tab1, tab2, tab3 = st.tabs(["Single Runtime Simu", "Battery Demand Simu", "Working Simu"])

# ========== 标签页1：单次续航时间模拟 ==========
with tab1:
    st.subheader("Parameter Input")
    battery_capacity = st.number_input("Battery Capacity(kwh)", min_value=0.0, value=150.0, step=10.0, key="battery_capacity")
    use_heater_tab1 = st.checkbox("Run Screed Heating", value=True, key="heater_tab1")
    if st.button("Calculate", type="primary", key="calc_duration"):
        usable_energy = battery_capacity * dod
        if use_heater_tab1:
            energy_heat = heater_power * heat_time
            if usable_energy < energy_heat:
                duration_heat_only = usable_energy / heater_power if heater_power > 0 else 0
                st.error(f"Battery usable energy {usable_energy:.2f} kWh is insufficient for 30 min heating (needs {energy_heat:.2f} kWh)")
                st.info(f"Only supports heating phase {duration_heat_only:.2f} hours")
            else:
                remaining = usable_energy - energy_heat
                if total_power_normal > 0:
                    normal_duration = remaining / total_power_normal
                    total_duration = heat_time + normal_duration
                    st.success("### Results")
                    st.metric("Usable energy", f"{usable_energy:.2f} kWh")
                    st.metric("Heating energy", f"{energy_heat:.2f} kWh")
                    st.metric("Normal operation duration", f"{normal_duration:.2f} hours")
                    st.metric("Total runtime", f"{total_duration:.2f} hours", delta=f"{total_duration*60:.0f} minutes")
                    if total_duration < 8:
                        st.info(f"💡 One charge can work for about {total_duration:.1f} hours, recommended to recharge every {total_duration:.1f} hours.")
                    else:
                        st.info(f"💡 One charge can cover a full shift (8 hours).")
                else:
                    st.warning("Normal operation power is zero, only heating phase")
        else:
            if total_power_all > 0:
                duration = usable_energy / total_power_all
                st.success("### Results")
                st.metric("Usable energy", f"{usable_energy:.2f} kWh")
                st.metric("Runtime", f"{duration:.2f} hours", delta=f"{duration*60:.0f} minutes")
                if duration < 8:
                    st.info(f"💡 One charge can work for about {duration:.1f} hours, recommended to recharge every {duration:.1f} hours.")
                else:
                    st.info(f"💡 One charge can cover a full shift (8 hours).")
            else:
                st.error("Total average power is zero, cannot calculate")

# ========== 标签页2：电池容量需求模拟 ==========
with tab2:
    st.subheader("Parameter Input")
    work_hours = st.number_input("Required total working time (hours)", min_value=0.0, value=4.0, step=0.5, key="work_hours_manual")
    use_heater_tab2 = st.checkbox("Run Screed Heating", value=True, key="heater_tab2")
    if st.button("Calculate", type="primary", key="calc_battery"):
        time_to_satisfy = work_hours
        if use_heater_tab2:
            if time_to_satisfy < heat_time:
                st.warning(f"Required time {time_to_satisfy} hours is less than initial heating time {heat_time} hours, will be calculated as full heating.")
                normal_hours = 0
                energy_normal = 0
                energy_total = heater_power * time_to_satisfy
            else:
                normal_hours = time_to_satisfy - heat_time
                energy_normal = total_power_normal * normal_hours
                energy_total = heater_power * heat_time + energy_normal
        else:
            energy_total = total_power_all * time_to_satisfy

        required_battery = energy_total / dod
        st.success("### Results")
        st.metric("Total required energy (usable)", f"{energy_total:.2f} kWh")
        if use_heater_tab2:
            colA, colB = st.columns(2)
            with colA:
                st.metric("Heating energy", f"{heater_power * heat_time:.2f} kWh")
            with colB:
                st.metric("Normal operation energy", f"{energy_normal:.2f} kWh" if 'energy_normal' in locals() else "0 kWh")
        st.metric("Required battery capacity", f"{required_battery:.2f} kWh", delta=f"Based on {dod:.0%} usable ratio")

# ========== 标签页3：实际工作模拟（拆分为两个子标签） ==========
with tab3:
     # 初始化存储模拟结果的 session_state 变量
    if "sim_result" not in st.session_state:
        st.session_state.sim_result = None
    if "charge_power" not in st.session_state:
        st.session_state.charge_power = 160.0
    if "target_soc" not in st.session_state:
        st.session_state.target_soc = 90.0
    if "slow_ratio" not in st.session_state:
        st.session_state.slow_ratio = 0.5

    sub_tab1, sub_tab2 = st.tabs(["Job Parameters", "Charging Parameters"])

    # ----- 子标签页1：工程参数 -----
    with sub_tab1:
        st.subheader("Parameter Input")
        road_length = st.number_input("Road length (m)", min_value=0.0, value=1000.0, step=100.0, key="road_length_tab3",
                                      help="Total paving length")
        paving_speed = st.number_input("Paving speed (m/min)", min_value=0.0, value=2.0, step=0.5, key="paving_speed_tab3",
                                       help="Paver traveling speed")
        charge_soc_threshold = st.number_input("Charging trigger SOC (%)", min_value=0.0, max_value=100.0, value=20.0, step=5.0,
                                               help="Start charging when battery SOC falls below this value. 0 means run until empty, 100 means always charging.")
        battery_capacity_tab3 = st.session_state.get("battery_capacity", 150.0)
        st.info(f"💡 Battery capacity is consistent with 'Single Runtime Simulation': **{battery_capacity_tab3:.1f} kWh**")
        use_heater_tab3 = st.checkbox("Run Screed Heating", value=True, key="heater_tab3")
        
        if st.button("Simulate", type="primary", key="simulate_work"):
            if paving_speed <= 0:
                st.error("Paving speed must be greater than 0")
            else:
                total_usable_energy = battery_capacity_tab3 * dod
                energy_heat = heater_power * heat_time if use_heater_tab3 else 0.0
                if use_heater_tab3 and total_usable_energy < energy_heat:
                    st.error(f"Battery usable energy {total_usable_energy:.2f} kWh is insufficient for 30 min heating (needs {energy_heat:.2f} kWh)")
                    st.session_state.sim_result = None
                else:
                    remaining_energy = total_usable_energy - energy_heat if use_heater_tab3 else total_usable_energy
                    work_power = total_power_normal if use_heater_tab3 else total_power_all
                    if work_power <= 0:
                        st.error("Normal operation average power is zero, cannot calculate")
                        st.session_state.sim_result = None
                    else:
                        paving_time = road_length / (paving_speed * 60)
                        threshold_energy = total_usable_energy * (charge_soc_threshold / 100.0)
                        target_energy = total_usable_energy * (st.session_state.target_soc / 100.0)
                        slow_threshold_energy = total_usable_energy * 0.9  # fixed 90%
                        
                        current_energy = remaining_energy
                        t_worked = 0.0
                        charge_count = 0
                        total_charge_time = 0.0
                        work_segments = []
                        
                        def compute_charge_time(current_energy, target_energy, total_energy, charge_power, slow_ratio):
                            if target_energy <= current_energy:
                                return 0.0
                            current_soc = current_energy / total_energy * 100.0
                            target_soc = target_energy / total_energy * 100.0
                            slow_threshold = 90.0
                            time = 0.0
                            if current_soc < slow_threshold and target_soc > current_soc:
                                end_soc = min(target_soc, slow_threshold)
                                energy_needed = (end_soc - current_soc) / 100.0 * total_energy
                                time += energy_needed / charge_power
                                current_soc = end_soc
                            if target_soc > slow_threshold and current_soc < target_soc:
                                energy_needed = (target_soc - max(current_soc, slow_threshold)) / 100.0 * total_energy
                                time += energy_needed / (charge_power * slow_ratio)
                            return time
                        
                        max_iter = 100
                        iter_count = 0
                        while t_worked < paving_time - 1e-6 and iter_count < max_iter:
                            iter_count += 1
                            if current_energy > threshold_energy:
                                dt = (current_energy - threshold_energy) / work_power
                            else:
                                dt = 0.0
                            if dt > 0:
                                dt = min(dt, paving_time - t_worked)
                                work_segments.append(dt)
                                t_worked += dt
                                current_energy -= dt * work_power
                            if t_worked >= paving_time - 1e-6:
                                break
                            # 需要充电
                            if current_energy < target_energy:
                                charge_energy_needed = target_energy - current_energy
                                charge_time = compute_charge_time(current_energy, target_energy, total_usable_energy,
                                                                  st.session_state.charge_power, st.session_state.slow_ratio)
                                total_charge_time += charge_time
                                charge_count += 1
                                current_energy = target_energy
                            else:
                                # 如果不需要充电（理论上不会），则强制退出
                                break
                        
                        total_time = paving_time + total_charge_time
                        single_charge_time = compute_charge_time(threshold_energy, target_energy, total_usable_energy,
                                                                 st.session_state.charge_power, st.session_state.slow_ratio)
                        
                        st.session_state.sim_result = {
                            "total_usable_energy": total_usable_energy,
                            "remaining_energy": remaining_energy,
                            "work_power": work_power,
                            "paving_time": paving_time,
                            "charge_soc_threshold": charge_soc_threshold,
                            "charge_count": charge_count,
                            "total_charge_time": total_charge_time,
                            "total_time": total_time,
                            "energy_per_charge": target_energy - threshold_energy,
                            "single_charge_time": single_charge_time,
                            "work_segments": work_segments
                        }
                        
                        st.success("### Simulation Results")
                        work_segments = work_segments
                        single_charge_time = single_charge_time
                        charge_count = charge_count
                        
                        for i in range(len(work_segments)):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(f"Continuous work segment {i+1}", f"{work_segments[i]:.2f} hours")
                            if i < charge_count:
                                with col2:
                                    st.metric(f"Charging time {i+1}", f"{single_charge_time:.2f} hours")
                            else:
                                with col2:
                                    st.markdown("")
                        
                        if len(work_segments) == 0:
                            st.metric("Continuous work time", "0 hours")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Actual paving time", f"{paving_time:.2f} hours")
                        with col2:
                            st.metric("Number of charges", f"{charge_count}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total time (paving + charging)", f"{total_time:.2f} hours")
                        with col2:
                            st.metric("Total charging time", f"{total_charge_time:.2f} hours")
                        
                        if charge_count == 0:
                            st.success("✅ One charge is sufficient for the job, no mid‑work charging needed.")
                        else:
                            st.info(f"🔋 Energy consumed per charge: {st.session_state.sim_result['energy_per_charge']:.2f} kWh")
                            if charge_soc_threshold > 0 and charge_soc_threshold < 100:
                                st.caption(f"Charging trigger SOC: {charge_soc_threshold}%  |  target SOC: {st.session_state.target_soc}%")
    
    # ----- 子标签页2：充电参数 -----
    with sub_tab2:
        st.subheader("Parameter Input")
        # 充电功率输入
        charge_power_input = st.number_input("Charging Power (kW)", min_value=0.0, value=st.session_state.charge_power, step=10.0, key="charge_power_input")
        st.session_state.charge_power = charge_power_input
        
        # 充电目标SOC
        target_soc_input = st.number_input("Charging target SOC (%)", min_value=0.0, max_value=100.0, value=st.session_state.target_soc, step=5.0, key="target_soc_input",
                                           help="Target SOC for each charging session (e.g., 90%). Charging stops when SOC reaches this value.")
        st.session_state.target_soc = target_soc_input
        
        # 降速后充电功率比例
        slow_ratio_input = st.number_input("Slow charging power ratio", min_value=0.0, max_value=1.0, value=st.session_state.slow_ratio, step=0.05, key="slow_ratio_input",
                                           help="After SOC exceeds 90%, charging power is multiplied by this ratio (e.g., 0.5 means half power).")
        st.session_state.slow_ratio = slow_ratio_input
        
        # 获取工程参数模拟结果
        sim = st.session_state.sim_result
        if sim is None:
            st.info("Please complete the simulation in the 'Job Parameters' tab first to calculate charging times.")
        else:
            if sim["charge_count"] == 0:
                st.success("According to the simulation, battery range is sufficient; no charging needed.")
            else:
                # 每次充电需要补充的度数
                charge_energy = sim["energy_per_charge"]
                st.metric("Energy required per charge", f"{charge_energy:.2f} kWh")
                if charge_power_input > 0:
                    # 重新计算单次充电时间（基于新的充电功率、目标SOC、降速比例）
                    # 从阈值SOC对应的能量充到目标SOC对应的能量
                    total_usable_energy = sim["total_usable_energy"]
                    threshold_soc = sim["charge_soc_threshold"]
                    threshold_energy = total_usable_energy * (threshold_soc / 100.0)
                    target_energy = total_usable_energy * (target_soc_input / 100.0)
                    if target_energy > threshold_energy:
                        # 辅助函数（同上）
                        def compute_charge_time(current_energy, target_energy, total_energy, charge_power, slow_ratio):
                            if target_energy <= current_energy:
                                return 0.0
                            current_soc = current_energy / total_energy * 100.0
                            target_soc = target_energy / total_energy * 100.0
                            slow_threshold = 90.0
                            time = 0.0
                            if current_soc < slow_threshold and target_soc > current_soc:
                                end_soc = min(target_soc, slow_threshold)
                                energy_needed = (end_soc - current_soc) / 100.0 * total_energy
                                time += energy_needed / charge_power
                                current_soc = end_soc
                            if target_soc > slow_threshold and current_soc < target_soc:
                                energy_needed = (target_soc - max(current_soc, slow_threshold)) / 100.0 * total_energy
                                time += energy_needed / (charge_power * slow_ratio)
                            return time
                        single_charge_time = compute_charge_time(threshold_energy, target_energy, total_usable_energy,
                                                                 charge_power_input, slow_ratio_input)
                    else:
                        single_charge_time = 0.0
                    st.metric("Single charge time", f"{single_charge_time:.2f} hours ({single_charge_time*60:.0f} minutes)")
                    # Total charging time
                    charge_count = sim["charge_count"]
                    total_charge_time = charge_count * single_charge_time
                    st.metric(f"Total charging time ({charge_count} charges)", f"{total_charge_time:.2f} hours ({total_charge_time*60:.0f} minutes)")
                    # U更新 session_state 中的总耗时（若充电功率改变，总耗时也会变）
                    total_time = sim["paving_time"] + total_charge_time
                    st.metric("Total time (paving + charging)", f"{total_time:.2f} hours")
                else:
                    st.error("Charging power must be greater than 0")
                
                # 提供一个按钮，在充电功率改变后重新计算充电时间（不重新模拟）
                if st.button("Re-calculate Charging Time", key="recalc_charge"):
                    if charge_power_input > 0:
                        total_usable_energy = sim["total_usable_energy"]
                        threshold_soc = sim["charge_soc_threshold"]
                        threshold_energy = total_usable_energy * (threshold_soc / 100.0)
                        target_energy = total_usable_energy * (target_soc_input / 100.0)
                        if target_energy > threshold_energy:
                            single_charge_time = compute_charge_time(threshold_energy, target_energy, total_usable_energy,
                                                                     charge_power_input, slow_ratio_input)
                        else:
                            single_charge_time = 0.0
                        total_charge_time = sim["charge_count"] * single_charge_time
                        st.success("Recalculation complete, see data above.")
                    else:
                        st.error("Charging power must be greater than 0")
                st.caption("Tip: After changing charging power, target SOC, or slow ratio, click 'Re-calculate Charging Time' to update charging times.")

# ========== Bottom instructions ==========
#st.divider()
#st.caption("""
#**Tips**:
#- Component parameters are fixed in the code; load factors are calculated by a custom function.
#- Battery available usage percentage is set in the sidebar (default 95%).
#- **Single Runtime Simulation**: Enter battery capacity to calculate theoretical runtime.
#- **Battery Capacity Demand Simulation**: Enter required working hours to calculate needed battery capacity.
#- **Actual Operation Simulation**:
#  - **Job Parameters**: Enter road length, paving speed, and charging trigger SOC (%). The system simulates the working process, automatically charging when battery SOC falls below the threshold, charging up to the set target SOC, and accounting for reduced charging power after 90% SOC. It displays each continuous work segment and its corresponding charging time, actual paving time, number of charges, total charging time, and total duration.
#  - **Charging Parameters**: Set charging power, target SOC, and slow charging power ratio. Based on the simulation results from the job parameters tab, it calculates single charge time and total charging time, and supports recalculating after parameter changes.
#- Results are for reference only.
#""")


