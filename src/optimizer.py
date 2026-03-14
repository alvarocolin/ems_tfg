from __future__ import annotations

import pandas as pd
from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Objective,
    Param,
    RangeSet,
    SolverFactory,
    Var,
    minimize,
    value,
)


def run_s3_optimizer(df_input: pd.DataFrame, params: dict, dt_h: float) -> pd.DataFrame:
    """
    Optimized EMS (S3) using MILP.

    Decision variables:
    - Pg[t]: grid import
    - Pc[t]: battery charge
    - Pd[t]: battery discharge
    - PVuse[t]: PV used
    - PVcurt[t]: PV curtailed
    - SOC[t]: battery state of charge
    - u[t]: binary variable to prevent simultaneous charge/discharge
    """
    n = len(df_input)

    load = df_input["load_kw"].to_numpy()
    pv = df_input["pv_kw"].to_numpy()
    price = df_input["price_eur_per_kwh"].to_numpy()

    E_kWh = params["E_kWh"]
    Pc_max = params["Pc_max"]
    Pd_max = params["Pd_max"]
    eta_c = params["eta_c"]
    eta_d = params["eta_d"]
    soc_min = params["soc_min"]
    soc_max = params["soc_max"]
    soc_res = params["soc_res"]
    soc_init = params["soc_init"]
    c_deg = params.get("c_deg", 0.0)

    m = ConcreteModel()
    m.T = RangeSet(0, n - 1)

    # Parameters
    m.demand = Param(m.T, initialize={t: float(load[t]) for t in range(n)})
    m.pv = Param(m.T, initialize={t: float(pv[t]) for t in range(n)})
    m.price = Param(m.T, initialize={t: float(price[t]) for t in range(n)})

    # Decision variables
    m.Pg = Var(m.T, domain=NonNegativeReals)
    m.Pc = Var(m.T, domain=NonNegativeReals)
    m.Pd = Var(m.T, domain=NonNegativeReals)
    m.PVuse = Var(m.T, domain=NonNegativeReals)
    m.PVcurt = Var(m.T, domain=NonNegativeReals)
    m.SOC = Var(m.T, domain=NonNegativeReals)

    # Binary variable:
    # u[t] = 1 -> charging allowed, discharging blocked
    # u[t] = 0 -> discharging allowed, charging blocked
    m.u = Var(m.T, domain=Binary)

    # PV split
    def pv_split_rule(m, t):
        return m.pv[t] == m.PVuse[t] + m.PVcurt[t]

    m.pv_split = Constraint(m.T, rule=pv_split_rule)

    # Power balance
    def balance_rule(m, t):
        return m.demand[t] == m.Pg[t] + m.PVuse[t] + m.Pd[t] - m.Pc[t]

    m.balance = Constraint(m.T, rule=balance_rule)

    # Battery power limits with no simultaneous charge/discharge
    def charge_limit_rule(m, t):
        return m.Pc[t] <= Pc_max * m.u[t]

    def discharge_limit_rule(m, t):
        return m.Pd[t] <= Pd_max * (1 - m.u[t])

    m.charge_limit = Constraint(m.T, rule=charge_limit_rule)
    m.discharge_limit = Constraint(m.T, rule=discharge_limit_rule)

    # SOC bounds
    def soc_bound_rule(m, t):
        return (soc_min, m.SOC[t], soc_max)

    m.soc_bounds = Constraint(m.T, rule=soc_bound_rule)

    # Reserve constraint
    def soc_reserve_rule(m, t):
        return m.SOC[t] >= soc_res

    m.soc_reserve = Constraint(m.T, rule=soc_reserve_rule)

    # Initial SOC
    m.soc_init = Constraint(expr=m.SOC[0] == soc_init)

    # Recommended: end-of-horizon SOC equal to initial SOC
    m.soc_final = Constraint(expr=m.SOC[n - 1] == soc_init)

    # SOC dynamics
    def soc_dyn_rule(m, t):
        if t == n - 1:
            return Constraint.Skip
        return m.SOC[t + 1] == (
            m.SOC[t]
            + (eta_c * m.Pc[t] * dt_h) / E_kWh
            - (m.Pd[t] * dt_h) / (eta_d * E_kWh)
        )

    m.soc_dyn = Constraint(m.T, rule=soc_dyn_rule)

    # Objective: energy purchase cost + battery degradation cost
    def objective_rule(m):
        grid_cost = sum(m.price[t] * m.Pg[t] * dt_h for t in m.T)
        degradation_cost = sum(c_deg * m.Pd[t] * dt_h for t in m.T)
        return grid_cost + degradation_cost

    m.obj = Objective(rule=objective_rule, sense=minimize)

    # Solve
    solver = SolverFactory("highs")
    result = solver.solve(m, tee=False)

    # Extract results
    df_result = pd.DataFrame({
        "timestamp": df_input["timestamp"],
        "Pg": [value(m.Pg[t]) for t in range(n)],
        "Pc": [value(m.Pc[t]) for t in range(n)],
        "Pd": [value(m.Pd[t]) for t in range(n)],
        "PVuse": [value(m.PVuse[t]) for t in range(n)],
        "PVcurt": [value(m.PVcurt[t]) for t in range(n)],
        "SOC": [value(m.SOC[t]) for t in range(n)],
        "u": [value(m.u[t]) for t in range(n)],
    })

    # Optional: useful for later analysis
    df_result["battery_deg_cost_eur"] = c_deg * df_result["Pd"] * dt_h

    return df_result