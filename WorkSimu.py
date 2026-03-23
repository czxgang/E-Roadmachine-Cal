import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="摊铺机能耗模拟计算器", layout="centered")
st.title("摊铺机能耗模拟计算器")

# ========== 1. 固定部件列表 ==========
FIXED_PARTS = pd.DataFrame({
    "部件名称": [
        "行走驱动", "输料刮板", "螺旋布料器", "熨平板加热",
        "振动系统", "振捣系统", "液压油缸系统", "辅助系统"
    ],
    "功率 (kW)": [30, 10, 16, 15, 8, 6.5, 10, 2]
})

# ========== 2. 自定义使用系数计算函数 ==========
def my_usage_factor_calculator(part_names):
    factors = []
    for name in part_names:
        if "油缸" in name:
            factors.append(30 / (10 * 60))  # 0.05
        elif "振动" in name:
            factors.append(0)
        elif "振捣" in name:
            factors.append(0.5)
        elif "行走" in name:
            factors.append(0.2)
        elif "输料" in name or "刮板" in name or "螺旋" in name:
            factors.append(0.5)
        elif "加热" in name:
            factors.append(0.0)
        elif "辅助" in name:
            factors.append(0.5)
        else:
            factors.append(1.0)
    return factors

computed_factors = my_usage_factor_calculator(FIXED_PARTS["部件名称"])
parts_df = FIXED_PARTS.copy()
parts_df["使用系数"] = computed_factors

# ========== 侧边栏：部件参数 + 电池参数 ==========
with st.sidebar:
    st.header("⚙️ 部件参数")
    st.caption("部件列表已固定，使用系数由自定义函数自动计算。")
    st.dataframe(
        parts_df,
        use_container_width=True,
        column_config={
            "部件名称": "部件名称",
            "功率 (kW)": st.column_config.NumberColumn("功率 (kW)", format="%.1f"),
            "使用系数": st.column_config.NumberColumn("使用系数", format="%.2f")
        }
    )
    total_power_all = (parts_df["功率 (kW)"] * parts_df["使用系数"]).sum()
    st.metric("所有部件平均功率", f"{total_power_all:.2f} kW")
    st.caption("包含所有部件按使用系数同时工作")

    st.divider()
    st.subheader("电池参数")
    dod_percent = st.number_input(
        "电池可用度数百分比 (%)", 
        min_value=10, max_value=100, value=95, step=5
    )
    dod = dod_percent / 100.0
    st.caption(f"当前可用比例：{dod:.0%}")

# ========== 公共数据准备 ==========
df = parts_df.copy()
heater_mask = df["部件名称"].str.contains("加热", na=False)
has_heater = heater_mask.any()
if has_heater:
    heater_power = df.loc[heater_mask, "功率 (kW)"].iloc[0]
else:
    heater_power = 0

if has_heater:
    normal_df = df[~heater_mask]
    total_power_normal = (normal_df["功率 (kW)"] * normal_df["使用系数"]).sum()
else:
    total_power_normal = total_power_all

heat_time = 0.5  # 小时

# ========== 主界面：三个标签页 ==========
tab1, tab2, tab3 = st.tabs(["单次续航时间模拟", "电池容量需求模拟", "实际工作模拟"])

# ========== 标签页1：单次续航时间模拟 ==========
with tab1:
    st.subheader("输入参数")
    battery_capacity = st.number_input("电池总容量 (kWh)", min_value=0.0, value=200.0, step=10.0, key="battery_capacity")
    use_heater_tab1 = st.checkbox("启用熨平板加热阶段", value=True, key="heater_tab1")
    if st.button("计算续航时间", type="primary", key="calc_duration"):
        usable_energy = battery_capacity * dod
        if use_heater_tab1:
            energy_heat = heater_power * heat_time
            if usable_energy < energy_heat:
                duration_heat_only = usable_energy / heater_power if heater_power > 0 else 0
                st.error(f"电池可用能量 {usable_energy:.2f} kWh 不足以完成30分钟加热（需要 {energy_heat:.2f} kWh）")
                st.info(f"仅能支持加热阶段 {duration_heat_only:.2f} 小时")
            else:
                remaining = usable_energy - energy_heat
                if total_power_normal > 0:
                    normal_duration = remaining / total_power_normal
                    total_duration = heat_time + normal_duration
                    st.success("### 计算结果")
                    st.metric("可用能量", f"{usable_energy:.2f} kWh")
                    st.metric("加热阶段能耗", f"{energy_heat:.2f} kWh")
                    st.metric("正常工作阶段时长", f"{normal_duration:.2f} 小时")
                    st.metric("总续航时间", f"{total_duration:.2f} 小时", delta=f"{total_duration*60:.0f} 分钟")
                    if total_duration < 8:
                        st.info(f"💡 一次充电可连续工作约 {total_duration:.1f} 小时，建议每 {total_duration:.1f} 小时充电一次。")
                    else:
                        st.info(f"💡 一次充电可满足一个工作班次（8小时）的需求。")
                else:
                    st.warning("正常工作阶段功率为0，只有加热阶段")
        else:
            if total_power_all > 0:
                duration = usable_energy / total_power_all
                st.success("### 计算结果")
                st.metric("可用能量", f"{usable_energy:.2f} kWh")
                st.metric("续航时间", f"{duration:.2f} 小时", delta=f"{duration*60:.0f} 分钟")
                if duration < 8:
                    st.info(f"💡 一次充电可连续工作约 {duration:.1f} 小时，建议每 {duration:.1f} 小时充电一次。")
                else:
                    st.info(f"💡 一次充电可满足一个工作班次（8小时）的需求。")
            else:
                st.error("总平均功率为0，无法计算")

# ========== 标签页2：电池容量需求模拟 ==========
with tab2:
    st.subheader("输入参数")
    work_hours = st.number_input("所需总工作时间 (小时)", min_value=0.0, value=4.0, step=0.5, key="work_hours_manual")
    use_heater_tab2 = st.checkbox("启用熨平板加热阶段", value=True, key="heater_tab2")
    if st.button("计算所需电池容量", type="primary", key="calc_battery"):
        time_to_satisfy = work_hours
        if use_heater_tab2:
            if time_to_satisfy < heat_time:
                st.warning(f"需求时间 {time_to_satisfy} 小时小于初期加热时间 {heat_time} 小时，将按全加热计算")
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
        st.success("### 计算结果")
        st.metric("所需总能量 (可用)", f"{energy_total:.2f} kWh")
        if use_heater_tab2:
            colA, colB = st.columns(2)
            with colA:
                st.metric("加热阶段能耗", f"{heater_power * heat_time:.2f} kWh")
            with colB:
                st.metric("正常工作能耗", f"{energy_normal:.2f} kWh" if 'energy_normal' in locals() else "0 kWh")
        st.metric("所需电池容量", f"{required_battery:.2f} kWh", delta=f"基于 {dod:.0%} 可用比例")

# ========== 标签页3：实际工作模拟（拆分为两个子标签）==========
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

    sub_tab1, sub_tab2 = st.tabs(["工程参数", "充电参数"])

    # ----- 子标签页1：工程参数 -----
    with sub_tab1:
        st.subheader("工程参数")
        road_length = st.number_input("路面长度 (m)", min_value=0.0, value=1000.0, step=100.0, key="road_length_tab3",
                                      help="待摊铺的路面总长度")
        paving_speed = st.number_input("摊铺速度 (m/min)", min_value=0.0, value=2.0, step=0.5, key="paving_speed_tab3",
                                       help="摊铺机行进速度")
        charge_soc_threshold = st.number_input("充电触发 SOC (%)", min_value=0.0, max_value=100.0, value=20.0, step=5.0,
                                               help="当电池剩余电量低于此百分比时开始充电。0表示一直用到没电才充，100表示随时充电。")
        battery_capacity_tab3 = st.session_state.get("battery_capacity", 200.0)
        st.info(f"💡 电池容量与「单次续航时间模拟」保持一致：**{battery_capacity_tab3:.1f} kWh**")
        use_heater_tab3 = st.checkbox("启用熨平板加热阶段", value=True, key="heater_tab3")
        
        if st.button("模拟实际工作", type="primary", key="simulate_work"):
            if paving_speed <= 0:
                st.error("摊铺速度必须大于0")
            else:
                total_usable_energy = battery_capacity_tab3 * dod
                energy_heat = heater_power * heat_time if use_heater_tab3 else 0.0
                if use_heater_tab3 and total_usable_energy < energy_heat:
                    st.error(f"电池可用能量 {total_usable_energy:.2f} kWh 不足以完成30分钟加热（需要 {energy_heat:.2f} kWh）")
                    st.session_state.sim_result = None
                else:
                    remaining_energy = total_usable_energy - energy_heat if use_heater_tab3 else total_usable_energy
                    work_power = total_power_normal if use_heater_tab3 else total_power_all
                    if work_power <= 0:
                        st.error("工作阶段平均功率为0，无法计算")
                        st.session_state.sim_result = None
                    else:
                        paving_time = road_length / (paving_speed * 60)
                        threshold_energy = total_usable_energy * (charge_soc_threshold / 100.0)
                        target_energy = total_usable_energy * (st.session_state.target_soc / 100.0)
                        slow_threshold_energy = total_usable_energy * 0.9  # 固定90%
                        
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
                        
                        st.success("### 模拟结果")
                        work_segments = work_segments
                        single_charge_time = single_charge_time
                        charge_count = charge_count
                        
                        for i in range(len(work_segments)):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(f"第{i+1}次连续工作时间", f"{work_segments[i]:.2f} 小时")
                            if i < charge_count:
                                with col2:
                                    st.metric(f"第{i+1}次充电时间", f"{single_charge_time:.2f} 小时")
                            else:
                                with col2:
                                    st.markdown("")
                        
                        if len(work_segments) == 0:
                            st.metric("连续工作时间", "0 小时")
                        
                        st.metric("实际摊铺时间", f"{paving_time:.2f} 小时")
                        st.metric("充电次数", f"{charge_count} 次")
                        st.metric("总充电时间", f"{total_charge_time:.2f} 小时")
                        st.metric("总耗时（摊铺 + 充电）", f"{total_time:.2f} 小时")
                        
                        if charge_count == 0:
                            st.success("✅ 一次充电即可完成工作，无需中途充电。")
                        else:
                            st.info(f"🔋 每次充电需补充电量：{st.session_state.sim_result['energy_per_charge']:.2f} kWh")
                            if charge_soc_threshold > 0 and charge_soc_threshold < 100:
                                st.caption(f"充电触发 SOC 阈值：{charge_soc_threshold}%")
                            st.caption(f"充电目标 SOC：{st.session_state.target_soc}% | 降速后充电功率比例：{st.session_state.slow_ratio*100:.0f}%")
    

    # ----- 子标签页2：充电参数 -----
    with sub_tab2:
        st.subheader("充电参数")
        # 充电功率输入
        charge_power_input = st.number_input("充电功率 (kW)", min_value=0.0, value=st.session_state.charge_power, step=10.0, key="charge_power_input")
        st.session_state.charge_power = charge_power_input
        
        # 充电目标SOC
        target_soc_input = st.number_input("充电目标 SOC (%)", min_value=0.0, max_value=100.0, value=st.session_state.target_soc, step=5.0, key="target_soc_input",
                                           help="每次充电的目标电量百分比（例如90%）。当SOC达到该值时停止充电。")
        st.session_state.target_soc = target_soc_input
        
        # 降速后充电功率比例
        slow_ratio_input = st.number_input("降速后充电功率比例", min_value=0.0, max_value=1.0, value=st.session_state.slow_ratio, step=0.05, key="slow_ratio_input",
                                           help="SOC超过90%后，充电功率将乘以该比例（例如0.5表示半功率充电）。")
        st.session_state.slow_ratio = slow_ratio_input
        
        # 获取工程参数模拟结果
        sim = st.session_state.sim_result
        if sim is None:
            st.info("请先在「工程参数」标签页中完成模拟，以计算充电时间。")
        else:
            if sim["charge_count"] == 0:
                st.success("根据当前模拟，电池续航已满足需求，无需充电。")
            else:
                # 每次充电需要补充的度数
                charge_energy = sim["energy_per_charge"]
                st.metric("每次充电所需度数", f"{charge_energy:.2f} kWh")
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
                    st.metric("单次充电时间", f"{single_charge_time:.2f} 小时 ({single_charge_time*60:.0f} 分钟)")
                    # 显示总充电时间
                    charge_count = sim["charge_count"]
                    total_charge_time = charge_count * single_charge_time
                    st.metric(f"总充电时间（充电 {charge_count} 次）", f"{total_charge_time:.2f} 小时 ({total_charge_time*60:.0f} 分钟)")
                    # 更新 session_state 中的总耗时（若充电功率改变，总耗时也会变）
                    total_time = sim["paving_time"] + total_charge_time
                    st.metric("总耗时（摊铺 + 充电）", f"{total_time:.2f} 小时")
                else:
                    st.error("充电功率必须大于0")
                
                # 提供一个按钮，在充电功率改变后重新计算充电时间（不重新模拟）
                if st.button("重新计算充电时间", key="recalc_charge"):
                    if charge_power_input > 0:
                        # 重新计算单次充电时间并显示
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
                        st.success("已重新计算，详见上方数据。")
                    else:
                        st.error("充电功率必须大于0")
                st.caption("提示：修改充电功率、目标SOC或降速比例后，点击“重新计算充电时间”可更新充电时间数据。")

# ========== 底部说明 ==========
st.divider()
st.caption("""
**使用说明**：
- 部件参数已在代码中固定，使用系数由自定义函数计算。
- 电池可用度数百分比在侧边栏统一设置（默认95%）。
- **单次续航时间模拟**：输入电池容量，计算理论续航时间。
- **电池容量需求模拟**：输入所需工作时间，计算所需电池容量。
- **实际工作模拟**：
  - 工程参数：输入路面长度、摊铺速度、充电触发 SOC（%）。系统将模拟工作过程，当电池剩余电量低于该阈值时自动充电，充电至设定的目标SOC，并考虑 SOC>90% 后充电功率下降。显示每次连续工作时间与对应充电时间（同行排列）、实际摊铺时间、充电次数、总充电时间及总耗时。
  - 充电参数：设置充电功率、充电目标 SOC、降速后充电功率比例，根据工程参数模拟结果自动计算每次充电时间和总充电时间，支持修改后重新计算。
- 结果仅供参考。
""")