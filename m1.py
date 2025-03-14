from gurobipy import Model, GRB, quicksum
import time


def run_cso_m1(params, n, m, l, r, run_id):
    model = Model(f"Model1_Run_{run_id}")
    
    # Variables
    X = model.addVars(m, n, vtype=GRB.BINARY, name="X")                 # Assignment matrix
    LOl = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="LOl")      # Leftover length
    YR = model.addVars(n, vtype=GRB.BINARY, name="YR")                  # Reusable leftover indicator
    WL = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="WL")        # Waste length
   
    # MODEL1 extra variables
    z = model.addVars(n, vtype=GRB.BINARY, name="z")                              
    YLR = model.addVars(n, vtype=GRB.BINARY, name="YLR")                # 1 if lefotver reutrns to stock


    # OBJECTIVE FUNCTION - minimize total waste length
    model.setObjective(quicksum(WL[j] for j in range(n)), GRB.MINIMIZE)

    # CONSTRAINTS:
    # 1 Ensures that each object’s length is completely allocated to item cuts or leftover stock
    for j in range(n):
        model.addConstr(quicksum(X[i, j] * r[i] for i in range(m)) + LOl[j] == l[j])
    
    # 2 Ensures that all ordered items are cut in the required quantities
    for i in range(m):
        model.addConstr(quicksum(X[i, j] for j in range(n)) == 1)
        
    # 3 If any items are cut from an object, the binary z_j is set to 1
    for j in range(n):
        model.addConstr(z[j] <= quicksum(X[i, j] for j in range(n)))
    
    # 4 Ensures z_j is 1 only if items are cut
    for j in range(n):
        model.addConstr(params['BIGM'] * z[j] >= quicksum(X[i, j] for j in range(n)))
        
    # 5 If the leftover is smaller than W, it can not be reused (YR_j = 0)
    for j in range(n):
        model.addConstr((LOl[j] -  params['W']) >= -params['BIGM'] * (1 - YR[j]) +  params['epsilon'])
    
    # 6 Ensures consistency in defining waste
    for j in range(n):
        model.addConstr((LOl[j] -  params['W']) <=  params['BIGM'] * (YR[j]))
        
    # 7 If waste exists (YR_j = 0), it contributes to WL_j
    for j in range(n):
        model.addConstr(WL[j] -  params['BIGM'] * (1 - YR[j]) <= 0)
        
    # 8 Ensures that waste is only counted when z_j = 1
    for j in range(n):
        model.addConstr(WL[j] -  params['BIGM'] * z[j] <= 0)
        
    # 9 Waste cannot exceed the leftover amount
    for j in range(n):
        model.addConstr(-LOl[j] + WL[j] <= 0)
    
    # 10 Ensures correct handling of waste
    for j in range(n):
        model.addConstr(LOl[j] - WL[j] +  params['BIGM'] * (1 - YR[j]) + params['BIGM'] * z[j] 
                        <= 2 * params['BIGM'])
        
    # 11 Ensures that an object can only become retail if it was actually used
    for j in range(n):
        model.addConstr(-z[j] + YLR[j] <= 0)
    
    # 12 An object cannot be both waste and retail
    for j in range(n):
        model.addConstr((1 - YR[j]) + YLR[j] <= 1)
        
    # 13 Ensures mutual exclusivity between waste, retail, and object usage
    for j in range(n):
        model.addConstr(z[j] - (1 - YR[j]) - YLR[j] <= 0)
    
    # 14 At most one object can become retail
    for j in range(n):
        model.addConstr(YLR[j] <= 1)
    

    start_time = time.time()
    model.setParam('OutputFlag', 0)  # Disable(0) / enable(1) detailed solver output
    model.optimize()
    elapsed_time = time.time() - start_time
    

    if model.status == GRB.OPTIMAL:    
        cuts = sum(sum(X[i, j].X for i in range(m)) - 1 
        + (1 if l[j] > sum(X[i, j].X * r[i] for i in range(m)) else 0)for j in range(n))
        
        used_bars = sum(1 for j in range(n) if sum(X[i, j].X for i in range(m)) > 0)
        
        waste = sum(WL[j].X for j in range(n))
        
        return {
            'run': run_id,
            'model': 'model1',
            'cuts': cuts,
            'cuts_cost': cuts * params['CC'],
            'waste': waste,
            'waste_cost': waste * params['CW'],
            'used_bars': used_bars,
            'total_cost': cuts * params['CC'] + waste * params['CW'],
            'solve_time': elapsed_time
            }
    else:
        return {
            'run': run_id, 
            'model': 'model1',
            'status': 'infeasible'
            }