import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

# ====================== 全局常量 ======================
HYDRAULIC_EFF = 0.95
HEAT_WORK_HOUR = 0.5
MAX_SIM_ITER = 200
CHARGE_RATE = 0.5
DEFAULT_BAT_CAP = 150.0

# 页面配置
st.set_page_config(page_title="Paver & Roller Energy Simulator", layout="wide")

# 全局样式优化
st.markdown("""
<style>
    .block-container {max-width: 1100px; margin: 0 auto;}
    div[data-testid="stSelectbox"],
    div[data-testid="stSlider"],
    div[data-testid="stNumberInput"] {max-width: 450px !important;}
    div[data-testid="stAlert"] {width: fit-content !important;}
</style>
""", unsafe_allow_html=True)

st.title("🚜 Construction Equipment Energy Simulator")

# ====================== 机型数据库（单一数据源）======================
PAVER_MODELS = {
    "BF200": {
        "Drive": 22.0, "Conveyor": 8.0, "Auger": 12.0, "Screed": 12.0,
        "Vibration": 6.0, "Compaction": 5.0, "HYD Cylinder": 8.0, "Lv System": 1.5
    },
    "SD1800We": {
        "Drive": 30.0, "Conveyor": 10.0, "Auger": 16.0, "Screed": 15.0,
        "Vibration": 8.0, "Compaction": 6.5, "HYD Cylinder": 10.0, "Lv System": 2.0
    },
    "SD25(Nodata)": {
        "Drive": 0.0, "Conveyor": 0.0, "Auger": 0.0, "Screed": 0.0,
        "Vibration": 0.0, "Compaction": 0.0, "HYD Cylinder": 0.0, "Lv System": 0.0
    },
    "SD11(Nodata)": {
        "Drive": 0.0, "Conveyor": 0.0, "Auger": 0.0, "Screed": 0.0,
        "Vibration": 0.0, "Compaction": 0.0, "HYD Cylinder": 0.0, "Lv System": 0.0
    },
    "BF800(Nodata)": {
        "Drive": 0.0, "Conveyor": 0.0, "Auger": 0.0, "Screed": 0.0,
        "Vibration": 0.0, "Compaction": 0.0, "HYD Cylinder": 0.0, "Lv System": 0.0
    },
}

# 压路机液压部件配置 + 效率配置
ROLLER_MODELS = {
    "BW138 (5t)": {
        "mass_kg": 4450.0, "speed_kmh": 5.0, "rolling_resistance": 0.018,
        "force_kn": 57.0, "amplitude_mm": 0.5, "frequency_hz": 56.0,
        "vib_efficiency": 0.85, "steer_power_peak": 6.0, "steer_duty_cycle": 30.0,
        "cooling_power": 3.0, "aux_power": 0.2, "drivetrain_efficiency": 0.88,
        # 液压部件功率
        "hydraulic_parts": {
            "Front travel Motor": 21,
            "Rear travel Motor": 21,
            "Front Vibration Motor": 8.75,
            "Rear Vibration Motor": 8.75,
            "Steering Motor": 10,
            "Cooling Motor": 3,
            "Aux": 1
        },
        # 多级效率
        "bat_eff": 0.98,
        "inv_eff": 0.97,
        "motor_eff": 0.95,
        "pump_eff": 0.90,
        "gear_eff": 0.95,
        "motor_hyd_eff": 0.90,
        "is_pure_motor": True
    },
    "BW203 AD-4 CL": {
        "mass_kg": 12800.0, "speed_kmh": 5.0, "rolling_resistance": 0.018,
        "force_kn": 200.0, "amplitude_mm": 0.8, "frequency_hz": 50.0,
        "vib_efficiency": 0.85, "steer_power_peak": 8.0, "steer_duty_cycle": 30.0,
        "cooling_power": 4.0, "aux_power": 2.5, "drivetrain_efficiency": 0.88,
        "hydraulic_parts": {
            "Front travel Motor": 40,
            "Rear travel Motor": 40,
            "Front Vibration Motor": 44,
            "Rear Vibration Motor": 44,
            "Steering Motor": 19.4,
            "Cooling Motor": 17.9,
            "Aux": 1
        },
        "bat_eff": 0.98,
        "inv_eff": 0.97,
        "motor_eff": 0.95,
        "pump_eff": 0.90,
        "gear_eff": 0.95,
        "motor_hyd_eff": 0.90,
        "is_pure_motor": True
    },
    "BW226 DH-5 PL": {
        "mass_kg": 25000.0, "speed_kmh": 5.0, "rolling_resistance": 0.025,
        "force_kn": 328.0, "amplitude_mm": 1.2, "frequency_hz": 26.0,
        "vib_efficiency": 0.85, "steer_power_peak": 10.0, "steer_duty_cycle": 20.0,
        "cooling_power": 0.0, "aux_power": 3.0, "drivetrain_efficiency": 0.88,
        "hydraulic_parts": {
            "Front travel Motor": 182,
            "Rear travel Motor": 257,
            "Front Vibration Motor": 116,
            "Rear Vibration Motor": 0,
            "Steering Motor": 18.7,
            "Cooling Motor": 12,
            "Aux": 1
        },
        "bat_eff": 0.98,
        "inv_eff": 0.97,
        "motor_eff": 0.96,
        "pump_eff": 0.9,
        "gear_eff": 0.95,
        "motor_hyd_eff": 0.9,
        "is_pure_motor": False
    },
    "BW120e(Nodata)": {
        "mass_kg": 0.0, "speed_kmh": 0.0, "rolling_resistance": 0.0,"force_kn": 0.0, "amplitude_mm": 0.0, "frequency_hz": 0.0,
        "vib_efficiency": 0.0, "steer_power_peak": 0.0, "steer_duty_cycle": 0.0,"cooling_power": 0.0, "aux_power": 0.0, "drivetrain_efficiency": 0.0,
        "hydraulic_parts": {
            "Front travel Motor": 0.0,"Rear travel Motor": 0.0,"Front Vibration Motor": 0.0,"Rear Vibration Motor": 0.0,"Steering Motor": 0.0,"Cooling Motor": 0.0,"Aux": 0.0
        },
        "bat_eff": 0.98,"inv_eff": 0.97,"motor_eff": 0.96,"pump_eff": 0.9,"gear_eff": 0.95,"motor_hyd_eff": 0.9,"is_pure_motor": False
    },
    "BW177e(Nodata)": {
        "mass_kg": 0.0, "speed_kmh": 0.0, "rolling_resistance": 0.0,"force_kn": 0.0, "amplitude_mm": 0.0, "frequency_hz": 0.0,
        "vib_efficiency": 0.0, "steer_power_peak": 0.0, "steer_duty_cycle": 0.0,"cooling_power": 0.0, "aux_power": 0.0, "drivetrain_efficiency": 0.0,
        "hydraulic_parts": {
            "Front travel Motor": 0.0,"Rear travel Motor": 0.0,"Front Vibration Motor": 0.0,"Rear Vibration Motor": 0.0,"Steering Motor": 0.0,"Cooling Motor": 0.0,"Aux": 0.0
        },
        "bat_eff": 0.98,"inv_eff": 0.97,"motor_eff": 0.96,"pump_eff": 0.9,"gear_eff": 0.95,"motor_hyd_eff": 0.9,"is_pure_motor": False
    },
    "CC900/1000e(Nodata)": {
        "mass_kg": 0.0, "speed_kmh": 0.0, "rolling_resistance": 0.0,"force_kn": 0.0, "amplitude_mm": 0.0, "frequency_hz": 0.0,
        "vib_efficiency": 0.0, "steer_power_peak": 0.0, "steer_duty_cycle": 0.0,"cooling_power": 0.0, "aux_power": 0.0, "drivetrain_efficiency": 0.0,
        "hydraulic_parts": {
            "Front travel Motor": 0.0,"Rear travel Motor": 0.0,"Front Vibration Motor": 0.0,"Rear Vibration Motor": 0.0,"Steering Motor": 0.0,"Cooling Motor": 0.0,"Aux": 0.0
        },
        "bat_eff": 0.98,"inv_eff": 0.97,"motor_eff": 0.96,"pump_eff": 0.9,"gear_eff": 0.95,"motor_hyd_eff": 0.9,"is_pure_motor": False
    },
    "CC1100/1200e(Nodata)": {
        "mass_kg": 0.0, "speed_kmh": 0.0, "rolling_resistance": 0.0,"force_kn": 0.0, "amplitude_mm": 0.0, "frequency_hz": 0.0,
        "vib_efficiency": 0.0, "steer_power_peak": 0.0, "steer_duty_cycle": 0.0,"cooling_power": 0.0, "aux_power": 0.0, "drivetrain_efficiency": 0.0,
        "hydraulic_parts": {
            "Front travel Motor": 0.0,"Rear travel Motor": 0.0,"Front Vibration Motor": 0.0,"Rear Vibration Motor": 0.0,"Steering Motor": 0.0,"Cooling Motor": 0.0,"Aux": 0.0
        },
        "bat_eff": 0.98,"inv_eff": 0.97,"motor_eff": 0.96,"pump_eff": 0.9,"gear_eff": 0.95,"motor_hyd_eff": 0.9,"is_pure_motor": False
    },
    "CX8(Nodata)": {
        "mass_kg": 0.0, "speed_kmh": 0.0, "rolling_resistance": 0.0,"force_kn": 0.0, "amplitude_mm": 0.0, "frequency_hz": 0.0,
        "vib_efficiency": 0.0, "steer_power_peak": 0.0, "steer_duty_cycle": 0.0,"cooling_power": 0.0, "aux_power": 0.0, "drivetrain_efficiency": 0.0,
        "hydraulic_parts": {
            "Front travel Motor": 0.0,"Rear travel Motor": 0.0,"Front Vibration Motor": 0.0,"Rear Vibration Motor": 0.0,"Steering Motor": 0.0,"Cooling Motor": 0.0,"Aux": 0.0
        },
        "bat_eff": 0.98,"inv_eff": 0.97,"motor_eff": 0.96,"pump_eff": 0.9,"gear_eff": 0.95,"motor_hyd_eff": 0.9,"is_pure_motor": False
    },
    "CS1400(Nodata)": {
        "mass_kg": 0.0, "speed_kmh": 0.0, "rolling_resistance": 0.0,"force_kn": 0.0, "amplitude_mm": 0.0, "frequency_hz": 0.0,
        "vib_efficiency": 0.0, "steer_power_peak": 0.0, "steer_duty_cycle": 0.0,"cooling_power": 0.0, "aux_power": 0.0, "drivetrain_efficiency": 0.0,
        "hydraulic_parts": {
            "Front travel Motor": 0.0,"Rear travel Motor": 0.0,"Front Vibration Motor": 0.0,"Rear Vibration Motor": 0.0,"Steering Motor": 0.0,"Cooling Motor": 0.0,"Aux": 0.0
        },
        "bat_eff": 0.98,"inv_eff": 0.97,"motor_eff": 0.96,"pump_eff": 0.9,"gear_eff": 0.95,"motor_hyd_eff": 0.9,"is_pure_motor": False
    },
    "CA1300(Nodata)": {
        "mass_kg": 0.0, "speed_kmh": 0.0, "rolling_resistance": 0.0,"force_kn": 0.0, "amplitude_mm": 0.0, "frequency_hz": 0.0,
        "vib_efficiency": 0.0, "steer_power_peak": 0.0, "steer_duty_cycle": 0.0,"cooling_power": 0.0, "aux_power": 0.0, "drivetrain_efficiency": 0.0,
        "hydraulic_parts": {
            "Front travel Motor": 0.0,"Rear travel Motor": 0.0,"Front Vibration Motor": 0.0,"Rear Vibration Motor": 0.0,"Steering Motor": 0.0,"Cooling Motor": 0.0,"Aux": 0.0
        },
        "bat_eff": 0.98,"inv_eff": 0.97,"motor_eff": 0.96,"pump_eff": 0.9,"gear_eff": 0.95,"motor_hyd_eff": 0.9,"is_pure_motor": False
    },
    "CA1500(Nodata)": {
        "mass_kg": 0.0, "speed_kmh": 0.0, "rolling_resistance": 0.0,"force_kn": 0.0, "amplitude_mm": 0.0, "frequency_hz": 0.0,
        "vib_efficiency": 0.0, "steer_power_peak": 0.0, "steer_duty_cycle": 0.0,"cooling_power": 0.0, "aux_power": 0.0, "drivetrain_efficiency": 0.0,
        "hydraulic_parts": {
            "Front travel Motor": 0.0,"Rear travel Motor": 0.0,"Front Vibration Motor": 0.0,"Rear Vibration Motor": 0.0,"Steering Motor": 0.0,"Cooling Motor": 0.0,"Aux": 0.0
        },
        "bat_eff": 0.98,"inv_eff": 0.97,"motor_eff": 0.96,"pump_eff": 0.9,"gear_eff": 0.95,"motor_hyd_eff": 0.9,"is_pure_motor": False
    },
}

# ====================== 工具函数 ======================
def build_paver_parts_df(model_name):
    data = PAVER_MODELS[model_name]
    df = pd.DataFrame({
        "Parts Name": list(data.keys()),
        "Power(kW)": list(data.values())
    })
    df["Load Factor"] = df["Parts Name"].apply(lambda x: {
        "Cylinder": 30/(10*60), "Vibration": 0, "Compaction": 0.5,
        "Drive": 0.2, "Auger": 0.5, "Conveyor": 0.5, "Screed": 0.0,
        "Lv System": 0.5
    }.get(next(k for k in ["Cylinder", "Vibration", "Compaction", "Drive", "Auger", "Conveyor", "Screed", "Lv System"] if k in x), 0.5))
    return df

def build_roller_hydraulic_df(model_name):
    data = ROLLER_MODELS[model_name]["hydraulic_parts"]
    df = pd.DataFrame({
        "Parts Name": list(data.keys()),
        "Power(kW)": list(data.values())
    })
    # 默认负载率（可编辑）
    df["Load Factor"] = 0.5
    return df

# ====================== 电池模型 ======================
soc_points = list(range(0, 101, 5))
discharge_ocv = [2.65, 3.13, 3.21, 3.22, 3.25, 3.27, 3.28, 3.29, 3.29, 3.3, 3.3, 3.3, 3.3, 3.31, 3.33, 3.33, 3.33, 3.33, 3.33, 3.33, 3.33]
charge_ocv   = [2.52, 3.18, 3.23, 3.26, 3.29, 3.3, 3.3, 3.31, 3.31, 3.31, 3.31, 3.31, 3.32, 3.34, 3.34, 3.34, 3.34, 3.34, 3.34, 3.34, 3.48]

class BatteryPack:
    def __init__(self):
        self.cells_series = 68
        self.packs_parallel = 3
        self.cell_capacity_Ah = 332
        self.total_capacity_Ah = self.cell_capacity_Ah * self.packs_parallel
        self.f_discharge = interp1d(soc_points, discharge_ocv, kind='linear', fill_value='extrapolate')
        self.f_charge = interp1d(soc_points, charge_ocv, kind='linear', fill_value='extrapolate')
        self.total_resistance = (self.cells_series * 0.9 / 1000) / self.packs_parallel

    def get_ocv(self, soc_percent, mode='discharge'):
        return float(self.f_discharge(soc_percent) if mode == 'discharge' else self.f_charge(soc_percent)) * self.cells_series

battery = BatteryPack()

def calculate_charge_time(soc_start, soc_end, charge_power_kW):
    if soc_end <= soc_start or charge_power_kW <= 0: return 0.0
    v_avg = (battery.get_ocv(soc_start, 'charge') + battery.get_ocv(soc_end, 'charge')) / 2
    i_avg = min((charge_power_kW * 1000) / v_avg, battery.total_capacity_Ah * CHARGE_RATE)
    return ((soc_end - soc_start) / 100 * battery.total_capacity_Ah) / i_avg if i_avg > 0 else 999

# ====================== Session 初始化 ======================
if "current_paver" not in st.session_state:
    st.session_state.current_paver = "SD1800We"
    st.session_state.paver_parts = build_paver_parts_df(st.session_state.current_paver)
if "current_roller" not in st.session_state:
    st.session_state.current_roller = "BW203 AD-4 CL"
    st.session_state.roller_hyd_parts = build_roller_hydraulic_df(st.session_state.current_roller)
if "sim_result" not in st.session_state:
    st.session_state.sim_result = None


# ====================== 侧边栏导航 ======================
with st.sidebar:
    st.header("📋 Navigation")
    equipment = st.selectbox("Select Equipment", ["Paver", "Roller"], key="eq_select")
    calc_mode = st.selectbox("Calculation Mode", ["Formula Calculation", "Hydraulic Power Based"], key="mode_select")
    st.divider()

    # 机型选择（无label）
    if equipment == "Roller":
        st.subheader("Machine type")
        selected_roller = st.selectbox("", list(ROLLER_MODELS.keys()), key="roller_select")
        if selected_roller != st.session_state.current_roller:
            st.session_state.current_roller = selected_roller
            st.session_state.roller_hyd_parts = build_roller_hydraulic_df(selected_roller)
            # 清除所有压路机相关组件的缓存
            for key in list(st.session_state.keys()):
                if key.startswith("r_"):
                    del st.session_state[key]
            st.rerun()

    if equipment == "Paver":
        st.subheader("Machine type")
        selected_paver = st.selectbox("", list(PAVER_MODELS.keys()), key="paver_select")
        if selected_paver != st.session_state.current_paver:
            st.session_state.current_paver = selected_paver
            st.session_state.paver_parts = build_paver_parts_df(selected_paver)
            st.rerun()

    # 摊铺机液压部件表
    if equipment == "Paver" and calc_mode == "Hydraulic Power Based":
        st.subheader("Paver Parts (Hydraulic)")
        edited_df = st.data_editor(
            st.session_state.paver_parts, use_container_width=True, num_rows="dynamic",
            column_config={
                "Parts Name": st.column_config.TextColumn(),
                "Power(kW)": st.column_config.NumberColumn(format="%.1f", step=1.0),
                "Load Factor": st.column_config.NumberColumn(format="%.2f", step=0.01)
            }, key="parts_editor"
        )
        st.session_state.paver_parts = edited_df
        avg_power = (edited_df["Power(kW)"] * edited_df["Load Factor"]).sum() / HYDRAULIC_EFF
        st.metric("Avg Power (Paver)", f"{avg_power:.2f} kW")

    # ✅ 压路机液压部件表（和摊铺机完全一样）
    if equipment == "Roller" and calc_mode == "Hydraulic Power Based":
        st.subheader("Roller Hydraulic Parts")
        edited_df = st.data_editor(
            st.session_state.roller_hyd_parts, use_container_width=True, num_rows="dynamic",
            column_config={
                "Parts Name": st.column_config.TextColumn(),
                "Power(kW)": st.column_config.NumberColumn(format="%.1f", step=1.0),
                "Load Factor": st.column_config.NumberColumn(format="%.2f", step=0.01)
            }, key="roller_hyd_editor"
        )
        st.session_state.roller_hyd_parts = edited_df
        avg_power = (edited_df["Power(kW)"] * edited_df["Load Factor"]).sum()
        st.metric("Hydraulic Total Power", f"{avg_power:.2f} kW")

    st.divider()
    st.subheader("Battery Spec")
    dod = st.number_input("Battery usable (%)", 10, 100, 95, 5) / 100

# ====================== 主页面：摊铺机 ======================
if equipment == "Paver":
    if calc_mode == "Hydraulic Power Based":
        df = st.session_state.paver_parts
        heater_power = df[df["Parts Name"].str.contains("Screed")]["Power(kW)"].sum()
        total_normal = (df[~df["Parts Name"].str.contains("Screed")]["Power(kW)"] * df["Load Factor"]).sum() / HYDRAULIC_EFF
        total_all = (df["Power(kW)"] * df["Load Factor"]).sum() / HYDRAULIC_EFF

        tab1, tab2, tab3 = st.tabs(["Single Runtime Simu", "Battery Demand Simu", "Working Simu"])

        with tab1:
            st.subheader("Parameter Input")
            bat_cap = st.number_input("Battery Capacity (kWh)", 0.0, value=DEFAULT_BAT_CAP, step=10.0, key="bat1")
            use_heater = st.checkbox("Run Screed Heating", value=True, key="heat1")
            if st.button("Calculate Runtime", type="primary", key="btn1"):
                usable = bat_cap * dod
                if use_heater:
                    heat_eng = heater_power * HEAT_WORK_HOUR
                    if usable < heat_eng:
                        st.error("Battery not enough for heating!")
                    else:
                        runtime = HEAT_WORK_HOUR + (usable - heat_eng) / total_normal
                        st.success("Calculation Results")
                        st.metric("Total runtime", f"{runtime:.2f} h")
                else:
                    runtime = usable / total_all
                    st.success("Calculation Results")
                    st.metric("Continuous runtime", f"{runtime:.2f} h")

        with tab2:
            st.subheader("Battery Capacity Calculation")
            work_hours = st.number_input("Required working hours", 0.0, 20.0, 4.0, 0.5, key="work2")
            use_heater = st.checkbox("Include 30min screed heating", value=True, key="heat2")
            if st.button("Calculate Battery Capacity", type="primary", key="btn2"):
                if use_heater:
                    if work_hours < HEAT_WORK_HOUR:
                        eng = heater_power * work_hours
                    else:
                        eng = heater_power * HEAT_WORK_HOUR + total_normal * (work_hours - HEAT_WORK_HOUR)
                else:
                    eng = total_all * work_hours
                req_bat = eng / dod
                st.success("Calculation Results")
                st.metric("Required battery capacity", f"{req_bat:.2f} kWh")

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
                        energy_heat = heater_power * HEAT_WORK_HOUR if use_heater_tab3 else 0.0
                        if use_heater_tab3 and total_usable_energy < energy_heat:
                            st.error(f"Battery usable energy {total_usable_energy:.2f} kWh is insufficient for 30 min heating (needs {energy_heat:.2f} kWh)")
                            st.session_state.sim_result = None
                        else:
                            remaining_energy = total_usable_energy - energy_heat if use_heater_tab3 else total_usable_energy
                            work_power = total_normal if use_heater_tab3 else total_all
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

    else:
        st.info("Paver - Formula Calculation Mode (Under Development)")

# ====================== 主页面：压路机 ======================
elif equipment == "Roller":
    if calc_mode == "Formula Calculation":
        st.header("🔋 Electric Roller - Formula Calculation")
        current_model = st.session_state.current_roller
        m = ROLLER_MODELS[current_model]

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Drive System")
            mass = st.number_input(
                "Operating mass (kg)", 4000.0, 40000.0,
                value=m["mass_kg"], step=500.0,
                key=f"r_mass_{current_model}"
            )
            speed = st.number_input(
                "Compaction speed (km/h)", 0.5, 10.0,
                value=m["speed_kmh"], step=0.1,
                key=f"r_speed_{current_model}"
            )
            roll_res = st.selectbox(
                "Rolling resistance coefficient",
                [0.012, 0.018, 0.025, 0.035, 0.050, 0.100],
                format_func=lambda x: {
                    0.012: "Asphalt (good) 0.012",
                    0.018: "Asphalt (normal) 0.018",
                    0.025: "Soil (compacted) 0.025",
                    0.035: "Soil (medium) 0.035",
                    0.050: "Soil (loose) 0.050",
                    0.100: "Soft/muddy 0.100"
                }.get(x, f"{x:.3f}"),
                index=[0.012,0.018,0.025,0.035,0.050,0.100].index(m["rolling_resistance"]),
                key=f"r_roll_{current_model}"
            )
        with col2:
            st.subheader("Vibration System")
            force = st.number_input(
                "Centrifugal force (kN)", 50.0, 500.0,
                value=m["force_kn"],
                key=f"r_force_{current_model}"
            )
            amp = st.number_input(
                "Amplitude (mm)", 0.3, 2.0,
                value=m["amplitude_mm"],
                key=f"r_amp_{current_model}"
            )
            freq = st.number_input(
                "Vibration frequency (Hz)", 20.0, 60.0,
                value=m["frequency_hz"],
                key=f"r_freq_{current_model}"
            )
            vib_eff = st.slider(
                "Vibration transfer efficiency", 0.5, 1.0,
                value=m["vib_efficiency"], step=0.05,
                key=f"r_vibe_{current_model}"
            )

        st.subheader("Steering & Auxiliary System")
        col3, col4 = st.columns(2)
        with col3:
            steer_p = st.number_input(
                "Steering peak power (kW)", 0.0, 30.0,
                value=m["steer_power_peak"],
                key=f"r_steer_{current_model}"
            )
            steer_duty = st.slider(
                "Steering duty cycle (%)", 0, 100,
                value=int(m["steer_duty_cycle"]),
                key=f"r_steer_duty_{current_model}"
            )
        with col4:
            cool_p = st.number_input(
                "Cooling system power (kW)", 0.0, 15.0,
                value=m["cooling_power"],
                key=f"r_cool_{current_model}"
            )
            aux_p = st.number_input(
                "Other auxiliary power (kW)", 0.0, 10.0,
                value=m["aux_power"],
                key=f"r_aux_{current_model}"
            )

        # 传动效率分解
        st.subheader("Powertrain Efficiency Breakdown")
        ef_col1, ef_col2, ef_col3 = st.columns(3)
        is_pure = m["is_pure_motor"]

        with ef_col1:
            bat_eff = st.number_input("Battery Efficiency", 0.80, 1.0, value=m["bat_eff"], step=0.01, key=f"bat_eff_{current_model}")
            if m["is_pure_motor"]:
                st.text_input("Pump Efficiency", value="/", disabled=True, key=f"pump_eff_{current_model}")
                pump_eff = 1.0
            else:
                pump_eff = st.number_input("Pump Efficiency", 0.80, 1.0, value=m["pump_eff"], step=0.01, key=f"pump_eff_{current_model}")
        with ef_col2:
            inv_eff = st.number_input("Inverter Efficiency", 0.80, 1.0, value=m["inv_eff"], step=0.01, key=f"inv_eff_{current_model}")
            if m["is_pure_motor"]:
                st.text_input("Gearbox Efficiency", value="/", disabled=True, key=f"gear_eff_{current_model}")
                gear_eff = 1.0
            else:
                gear_eff = st.number_input("Gearbox Efficiency", 0.80, 1.0, value=m["gear_eff"], step=0.01, key=f"gear_eff_{current_model}")
        with ef_col3:
            motor_eff = st.number_input("eMotor Efficiency", 0.80, 1.0, value=m["motor_eff"], step=0.01, key=f"motor_eff_{current_model}")
            if m["is_pure_motor"]:
                st.text_input("Hydraulic Motor Efficiency", value="/", disabled=True, key=f"hyd_motor_{current_model}")
                hyd_motor_eff = 1.0
            else:
                hyd_motor_eff = st.number_input("Hydraulic Motor Efficiency", 0.80, 1.0, value=m["motor_hyd_eff"], step=0.01, key=f"hyd_motor_{current_model}")


        # 实时总效率
        if is_pure:
            total_drive_eff = bat_eff * inv_eff * motor_eff
        else:
            total_drive_eff = bat_eff * inv_eff * motor_eff * pump_eff * gear_eff * hyd_motor_eff

        st.metric("Total Drivetrain Efficiency", f"{total_drive_eff:.3f}")

        work_hours = st.number_input(
            "Continuous working hours", 0.0, 24.0, 1.0, 0.5,
            key=f"r_work_{current_model}"
        )

        if st.button("Calculate Roller Energy", type="primary", key=f"r_btn_{current_model}"):
            g = 9.81
            speed_ms = speed / 3.6
            p_travel = (mass * g * roll_res * speed_ms) / 1000

            omega = 2 * np.pi * freq
            p_vib = (0.5 * force * 1000 * (amp/1000) * omega * vib_eff) / 1000

            p_steer_avg = steer_p * (steer_duty / 100)
            p_aux_total = cool_p + aux_p
            p_main = (p_travel + p_vib) / total_drive_eff
            total_power = p_main + p_steer_avg + p_aux_total
            total_energy = total_power * work_hours

            st.success("Roller Energy Calculation Result")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Average working power", f"{total_power:.1f} kW")
                st.metric("Total energy consumption", f"{total_energy:.1f} kWh")
            with c2:
                st.metric("Working duration", f"{work_hours:.1f} h")
                max_runtime = (DEFAULT_BAT_CAP * dod) / total_power
                st.metric("Current battery runtime", f"{max_runtime:.2f} h")

            with st.expander("Detailed power breakdown"):
                st.write(f"Driving power: {p_travel:.1f} kW")
                st.write(f"Vibration working power: {p_vib:.1f} kW")
                st.write(f"Average steering power: {p_steer_avg:.1f} kW")
                st.write(f"Auxiliary total power: {p_aux_total:.1f} kW")
                st.write(f"Total drivetrain efficiency: {total_drive_eff:.3f}")

    # ✅ 新增：压路机液压功率计算模式（完整功能）
    else:
        st.header("⚙️ Roller - Hydraulic Power Based")
        current_model = st.session_state.current_roller
        m = ROLLER_MODELS[current_model]
        df_hyd = st.session_state.roller_hyd_parts

        # 实时计算液压总功率
        hyd_total_power = (df_hyd["Power(kW)"] * df_hyd["Load Factor"]).sum()

        # 传动效率配置（和公式模式完全一致）
        st.subheader("Powertrain Efficiency Breakdown")
        ef_col1, ef_col2, ef_col3 = st.columns(3)
        is_pure = m["is_pure_motor"]

        with ef_col1:
                bat_eff = st.number_input("Battery Efficiency", 0.80, 1.0, value=m["bat_eff"], step=0.01, key=f"bat_eff_{current_model}")
                pump_eff_hyd = st.number_input("Pump Efficiency", 0.75, 1.0, value=m["pump_eff"], step=0.01, key=f"h_pump_{current_model}")
        with ef_col2:
                inv_eff = st.number_input("Inverter Efficiency", 0.80, 1.0, value=m["inv_eff"], step=0.01, key=f"inv_eff_{current_model}")
                gear_eff_hyd = st.number_input("Gearbox Efficiency", 0.75, 1.0, value=m["gear_eff"], step=0.01, key=f"h_gear_{current_model}")
        with ef_col3:
                motor_eff = st.number_input("eMotor Efficiency", 0.80, 1.0, value=m["motor_eff"], step=0.01, key=f"motor_eff_{current_model}")
                hyd_motor_eff_hyd = st.number_input("Hydraulic Motor Efficiency", 0.75, 1.0, value=m["motor_hyd_eff"], step=0.01, key=f"h_hydmotor_{current_model}")

        # 实时总效率

        total_eff_hyd = bat_eff * inv_eff * motor_eff * pump_eff_hyd * gear_eff_hyd * hyd_motor_eff_hyd

        st.metric("Total Drivetrain Efficiency", f"{total_eff_hyd:.3f}")
        total_input_power = hyd_total_power / total_eff_hyd

        # 计算区域
        st.subheader("Energy Calculation")
        work_hours_hyd = st.number_input("Working Hours", 0.0, 10.0, 4.0, 0.5, key="hyd_hours")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Hydraulic Output Power", f"{hyd_total_power:.2f} kW")
            st.metric("Total Input Power (with efficiency)", f"{total_input_power:.2f} kW")
            total_energy_hyd = total_input_power * work_hours_hyd
            st.metric("Total Energy Consumption", f"{total_energy_hyd:.2f} kWh")
        with col_b:
            ()

st.divider()
st.caption("Simulation results are for engineering reference only")
