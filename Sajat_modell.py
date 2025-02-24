import pyomo.environ as pyo
import numpy as np
from pyomo.environ import *
from pyomo.opt import SolverFactory


model = pyo.ConcreteModel()

# Data
rhossz = [200, 200, 200, 150, 150, 150]
ohossz = [100, 80, 70, 70, 70, 60, 60, 50, 45, 40, 30, 30, 30]
hulladek_hatar = 45
egysegnyi_hulladek_ktg = 100
vagas_ktg = 400
M = 1000000


# Sets
model.R = RangeSet(len(rhossz))
model.O = RangeSet(len(ohossz))


# Decision variables
model.x = Var(model.O, model.R, domain=Binary)
model.marad = Var(model.R, domain=NonNegativeReals)
model.marad_e = Var(model.R, domain=Binary)
model.szemet = Var(model.R, domain=NonNegativeReals)
model.y = Var(model.R, domain=Binary)
model.haszn_e = Var(model.R, domain=Binary)

# Objective function: Minimize total cost
model.obj = Objective(
    expr=(sum((sum(model.x[o, r] for o in model.O) - 1 + model.marad_e[r]) * vagas_ktg for r in model.R)
          + sum(model.szemet[r] * egysegnyi_hulladek_ktg for r in model.R)
          + sum(model.haszn_e[r] for r in model.R)),
    sense=minimize
)

# Constraints
# (1) Rod length equals sum of cuts plus leftover
model.rod_length_cons = ConstraintList()
for r in model.R:
    model.rod_length_cons.add(
        sum(model.x[o, r] * ohossz[o - 1] for o in model.O) + model.marad[r] == rhossz[r - 1]
    )

# (2) Each order must be served by exactly one rod
model.order_cons = ConstraintList()
for o in model.O:
    model.order_cons.add(sum(model.x[o, r] for r in model.R) == 1)

# (3) Leftover indicator constraint
model.leftover_indicator = ConstraintList()
for r in model.R:
    model.leftover_indicator.add(model.marad_e[r] >= model.marad[r] / rhossz[r - 1])

# (4) Waste threshold condition
model.waste_condition_1 = ConstraintList()
model.waste_condition_2 = ConstraintList()
for r in model.R:
    model.waste_condition_1.add(model.marad[r] - model.szemet[r] <= M * model.y[r])
    model.waste_condition_2.add(hulladek_hatar - model.marad[r] <= M * (1 - model.y[r]))

# (5) Rod usage indicator
model.rod_usage = ConstraintList()
for r in model.R:
    model.rod_usage.add(model.haszn_e[r] >= 1 - (model.marad[r] / rhossz[r - 1]))


# Solve model
opt = SolverFactory('gurobi')
results = opt.solve(model)


# Results with counting cuts and used rods
cut_count = 0
used_rods = 0

for r in model.R:
    rod_used = pyo.value(model.haszn_e[r])
    leftover = pyo.value(model.marad[r])
    if rod_used > 0.5:
        used_rods += 1
        orders_cut = [ohossz[o - 1] for o in model.O if pyo.value(model.x[o, r]) > 0.5]
        cuts_in_rod = len(orders_cut) - 1 if leftover == 0 else len(orders_cut)
        cut_count += cuts_in_rod


# Printing results
print('Total cost:', pyo.value(model.obj))
print('Total cuts made:', cut_count)
print('Total rods used:', used_rods)

for r in model.R:
    print(f'Rod R{r}:')
    print(f'  Used: {pyo.value(model.haszn_e[r])}')
    print(f'  Leftover: {pyo.value(model.marad[r])}')
    print(f'  Waste: {pyo.value(model.szemet[r])}')
    
    orders_in_rod = []
    for o in model.O:
        if pyo.value(model.x[o, r]) > 0.5:
            orders_in_rod.append(ohossz[o - 1])
            print(f'    Order O{o}: {ohossz[o - 1]}')
    cuts_in_rod = len(orders_in_rod) - 1 if pyo.value(model.marad[r]) == 0 else len(orders_in_rod)
    print(f'  Cuts in this rod: {cuts_in_rod}')
