from krrt.sat.CNF import OptimizedLevelWeightedFormula

import math

def readBNN(directory):
    
    layers = []
    weights = {}
    BNNFile = open(directory,"r")
    data = BNNFile.read().splitlines()
    
    layerSizeIndex = 1
    input = 0
    output = 0
    layer = 0
    out = 0
    
    for index, dat in enumerate(data):
        if (index == layerSizeIndex):
            input, output = dat.split(",")
            layerSizeIndex = int(output) + layerSizeIndex + 1
            layers.append([int(input),int(output)])
            layer += 1
            out = 0
        else:
            for inp in range(int(input)):
                weight = 0
                if (dat[int(inp)] == '0'):
                    weight = -1
                elif (dat[int(inp)] == '1'):
                    weight = 1
                else:
                    weight = 0
                weights[(layer-1, inp, out)] = weight
            out += 1

    return weights, layers

def readNormalization(directory, layers):
    
    nLayers = len(layers)
    normalization = []
    NormalizationFile = open(directory,"r")
    data = NormalizationFile.read().splitlines()
    
    for index, dat in enumerate(data):
        if index > 0:
            normalization.append(dat.split(","))

    return normalization

def readInitial(directory):
    
    initial = []
    initialFile = open(directory,"r")
    data = initialFile.read().splitlines()
    
    for dat in data:
        initial.append(dat.split(","))

    return initial

def readGoals(directory):
    
    goals = []
    goalsFile = open(directory,"r")
    data = goalsFile.read().splitlines()
    
    for dat in data:
        goals.append(dat.split(","))

    return goals

def readConstraints(directory):
    
    constraints = []
    constraintsFile = open(directory,"r")
    data = constraintsFile.read().splitlines()
    
    for dat in data:
        constraints.append(dat.split(","))

    return constraints

def readTransitions(directory):
    
    transitions = []
    transitionsFile = open(directory,"r")
    data = transitionsFile.read().splitlines()
    
    for dat in data:
        transitions.append(dat.split(","))
    
    return transitions

def readReward(directory):
    
    reward = []
    rewardFile = open(directory,"r")
    data = rewardFile.read().splitlines()
    
    for dat in data:
        reward.append(dat.split(","))
    
    return reward

def readVariables(directory):
    
    A = []
    AData = []
    S = []
    SData = []
    SLabel = []
    
    variablesFile = open(directory,"r")
    data = variablesFile.read().splitlines()
    
    for dat in data:
        variables = dat.split(",")
        for var in variables:
            if "action:" in var or "action_data:" in var:
                if "_data:" in var:
                    AData.append(var.replace("action_data: ",""))
                    A.append(var.replace("action_data: ",""))
                else:
                    A.append(var.replace("action: ",""))
            else:
                if "_data:" in var or "_data_label:" in var:
                    if "_label:" in var:
                        SData.append(var.replace("state_data_label: ",""))
                        SLabel.append(var.replace("state_data_label: ",""))
                        S.append(var.replace("state_data_label: ",""))
                    else:
                        SData.append(var.replace("state_data: ",""))
                        S.append(var.replace("state_data: ",""))
                else:
                    if "_label:" in var:
                        SLabel.append(var.replace("state_label: ",""))
                        S.append(var.replace("state_label: ",""))
                    else:
                        S.append(var.replace("state: ",""))

    return A, AData, S, SData, SLabel

def encode_fd_sat_plan(domain, instance, horizon, optimize):
    
    weights, layers = readBNN("./bnn/bnn_"+domain+"_"+instance+".txt")
    
    normalization = readNormalization("./normalization/normalization_"+domain+"_"+instance+".txt", layers)
    
    initial = readInitial("./translation/initial_"+domain+"_"+instance+".txt")
    goals = readGoals("./translation/goals_"+domain+"_"+instance+".txt")
    constraints = readConstraints("./translation/constraints_"+domain+"_"+instance+".txt")
    A, AData, S, SData, SLabel = readVariables("./translation/pvariables_"+domain+"_"+instance+".txt")
    
    nHiddenLayers = len(layers)-1
    VARINDEX = 1
    
    #SLabel = S[:layers[len(layers)-1][1]] #SLabel = S Sometimes, you can also assume this is true.
    
    transitions = []
    if len(SLabel) < len(S):
        transitions = readTransitions("./translation/transitions_"+domain+"_"+instance+".txt")
    reward = []
    if optimize == "True":
        reward = readReward("./translation/reward_"+domain+"_"+instance+".txt")
    
    formula = OptimizedLevelWeightedFormula()

    # Create vars for each action a, time step t
    x = {}
    for a in A:
        for t in range(horizon):
            x[(a,t)] = VARINDEX
            VARINDEX += 1

    # Create vars for each state a, time step t
    y = {}
    for s in S:
        for t in range(horizon+1):
            y[(s,t)] = VARINDEX
            VARINDEX += 1

    # Create vars for each activation node z at depth d, width w, time step t
    z = {}
    for t in range(horizon):
        for d in range(nHiddenLayers):
            for w in range(layers[d][1]):
                z[(d,w,t)] = VARINDEX
                VARINDEX += 1

    # Constraints
    for t in range(horizon+1):
        for constraint in constraints:
            variables = constraint[:-2]
            literals = []
            if set(A).isdisjoint(variables) or t < horizon: # for the last time step, only consider constraints that include states variables-only
                for var in variables:
                    if var in A or var[1:] in A:
                        if var[0] == "~":
                            literals.append(-x[(var[1:],t)])
                        else:
                            literals.append(x[(var,t)])
                    else:
                        if var[0] == "~":
                            literals.append(-y[(var[1:],t)])
                        else:
                            literals.append(y[(var,t)])
                RHS = int(constraint[len(constraint)-1])
                if "<=" == constraint[len(constraint)-2]:
                    VARINDEX, formula = addAtMostKSeq(literals, RHS, formula, VARINDEX)
                elif ">=" == constraint[len(constraint)-2]:
                    literals = [-i for i in literals]
                    RHS = len(literals) - RHS
                    VARINDEX, formula = addAtMostKSeq(literals, RHS, formula, VARINDEX)
                else:
                    VARINDEX, formula = addExactlyKSeq(literals, RHS, formula, VARINDEX)

    # Known Transitions
    for t in range(horizon):
        for transition in transitions:
            variables = transition[:-2]
            literals = []
            for var in variables:
                if var in A or var[1:] in A:
                    if var[0] == "~":
                        literals.append(-x[(var[1:],t)])
                    else:
                        literals.append(x[(var,t)])
                else:
                    if var[0] == "~":
                        if var[len(var)-1] == "'":
                            literals.append(-y[(var[1:-1],t+1)])
                        else:
                            literals.append(-y[(var[1:],t)])
                    else:
                        if var[len(var)-1] == "'":
                            literals.append(y[(var[:-1],t+1)])
                        else:
                            literals.append(y[(var,t)])
            RHS = int(transition[len(transition)-1])
            if "<=" == transition[len(transition)-2]:
                VARINDEX, formula = addAtMostKSeq(literals, RHS, formula, VARINDEX)
            elif ">=" == transition[len(transition)-2]:
                literals = [-i for i in literals]
                RHS = len(literals) - RHS
                VARINDEX, formula = addAtMostKSeq(literals, RHS, formula, VARINDEX)
            else:
                VARINDEX, formula = addExactlyKSeq(literals, RHS, formula, VARINDEX)

    # Set initial state
    for init in initial:
        variables = init[:-2]
        literals = []
        for var in variables:
            if var[0] == "~":
                literals.append(-y[(var[1:],0)])
            else:
                literals.append(y[(var,0)])
        RHS = int(init[len(init)-1])
        if "<=" == init[len(init)-2]:
            VARINDEX, formula = addAtMostKSeq(literals, RHS, formula, VARINDEX)
        elif ">=" == init[len(init)-2]:
            literals = [-i for i in literals]
            RHS = len(literals) - RHS
            VARINDEX, formula = addAtMostKSeq(literals, RHS, formula, VARINDEX)
        else:
            VARINDEX, formula = addExactlyKSeq(literals, RHS, formula, VARINDEX)

    # Set goal state
    for goal in goals:
        variables = goal[:-2]
        literals = []
        for var in variables:
            if var[0] == "~":
                literals.append(-y[(var[1:],horizon)])
            else:
                literals.append(y[(var,horizon)])
        RHS = int(goal[len(goal)-1])
        if "<=" == goal[len(goal)-2]:
            VARINDEX, formula = addAtMostKSeq(literals, RHS, formula, VARINDEX)
        elif ">=" == goal[len(goal)-2]:
            literals = [-i for i in literals]
            RHS = len(literals) - RHS
            VARINDEX, formula = addAtMostKSeq(literals, RHS, formula, VARINDEX)
        else:
            VARINDEX, formula = addExactlyKSeq(literals, RHS, formula, VARINDEX)

    # Set node activations
    for t in range(horizon):
        for d in range(nHiddenLayers):
            for out in range(layers[d][1]):
                positiveInputLiterals = []
                
                layersize = 0
                
                if d == 0: # input is state or actions
                    for inp, a in enumerate(AData):
                        if weights[(d, inp, out)] > 0:
                            positiveInputLiterals.append(x[(a,t)])
                            layersize += 1
                        elif weights[(d, inp, out)] < 0:
                            positiveInputLiterals.append(-x[(a,t)])
                            layersize += 1
                    for i, s in enumerate(SData):
                        inp = i + len(AData)
                        if weights[(d, inp, out)] > 0:
                            positiveInputLiterals.append(y[(s,t)])
                            layersize += 1
                        elif weights[(d, inp, out)] < 0:
                            positiveInputLiterals.append(-y[(s,t)])
                            layersize += 1
                else:
                    for inp in range(layers[d][0]):
                        if weights[(d, inp, out)] > 0:
                            positiveInputLiterals.append(z[(d-1,inp,t)])
                            layersize += 1
                        elif weights[(d, inp, out)] < 0:
                            positiveInputLiterals.append(-z[(d-1,inp,t)])
                            layersize += 1
            
                positive_threshold = int(math.ceil(layersize/2.0 + float(normalization[d][out])/2.0))
                negative_threshold = layersize - positive_threshold + 1
                
                if positive_threshold >= layersize + 1:
                    formula.addClause([-z[(d,out,t)]])
                elif negative_threshold >= layersize + 1:
                    formula.addClause([z[(d,out,t)]])
                else:
                    if positive_threshold < negative_threshold:
                        VARINDEX, formula = addCardNetworkBinaryActivation(positiveInputLiterals, positive_threshold, formula, VARINDEX, z[(d,out,t)])
                    else:
                        negativeInputLiterals = [-i for i in positiveInputLiterals]
                        VARINDEX, formula = addCardNetworkBinaryActivation(negativeInputLiterals, negative_threshold, formula, VARINDEX, -z[(d,out,t)])

    # Predict the next state using BNNs
    for t in range(horizon):
        d = nHiddenLayers
        for out, s in enumerate(SLabel):
            positiveInputLiterals = []
            
            layersize = 0
            
            for inp in range(layers[d][0]):
                if weights[(d, inp, out)] > 0:
                    positiveInputLiterals.append(z[(d-1,inp,t)])
                    layersize += 1
                elif weights[(d, inp, out)] < 0:
                    positiveInputLiterals.append(-z[(d-1,inp,t)])
                    layersize += 1
        
            positive_threshold = int(math.ceil(layersize/2.0 + float(normalization[d][out])/2.0))
            negative_threshold = layersize - positive_threshold + 1
            
            if positive_threshold >= layersize + 1:
                literals.append([-y[(s,t+1)]])
            elif negative_threshold >= layersize + 1:
                literals.append([y[(s,t+1)]])
            else:
                if positive_threshold < negative_threshold:
                    VARINDEX, formula = addCardNetworkBinaryActivation(positiveInputLiterals, positive_threshold, formula, VARINDEX, y[(s,t+1)])
                else:
                    negativeInputLiterals = [-i for i in positiveInputLiterals]
                    VARINDEX, formula = addCardNetworkBinaryActivation(negativeInputLiterals, negative_threshold, formula, VARINDEX, -y[(s,t+1)])

    if optimize == "True":
        for t in range(horizon):
            for var, weight in reward:
                if var in A or var[1:] in A:
                    if var[0] == "~":
                        formula.addClause([-x[(var[1:],t)]], float(weight), 1)
                    else:
                        formula.addClause([x[(var,t)]], float(weight), 1)
                else:
                    if var[0] == "~":
                        formula.addClause([-y[(var[1:],t+1)]], float(weight), 1)
                    else:
                        formula.addClause([y[(var,t+1)]], float(weight), 1)

    print ''
    print "Number of Variables: %d" % formula.num_vars
    print "Number of Clauses: %d" % formula.num_clauses
    print "Number of Hard Clauses: %d" % len(formula.getHardClauses())
    if optimize == "True":
        print "Number of Soft Clauses: %d" % len(formula.getSoftClauses())
        print "Maximum Weight: %d" % formula.top_weight
        formula.writeCNF(domain+"_"+instance+"_"+str(horizon)+'.wcnf')
    else:
        formula.writeCNF(domain+"_"+instance+"_"+str(horizon)+'.cnf', hard=True)
    print ''

    return

def addAtMostKSeq(x, k, formula, VARINDEX): # Sinz (2005 encoding)
    
    n = len(x)
    
    if n == 1:
        if k >= 1:
            return VARINDEX, formula
        else:
            x = [-i for i in x]
            formula.addClause(x)
        return VARINDEX, formula
    elif n - k == 1:
        x = [-i for i in x]
        formula.addClause(x)
        return VARINDEX, formula
    
    # Create the vars for  partial sum bits
    s = {}
    for i in range(n):
        for j in range(k):
            s[(i,j)] = VARINDEX
            VARINDEX += 1

    formula.addClause([-x[(0)], s[(0,0)]])
    
    for j in range(1,k):
        formula.addClause([-s[(0,j)]])

    for i in range(1,n-1):
        formula.addClause([-x[(i)], s[(i,0)]])
        formula.addClause([-s[(i-1,0)], s[(i,0)]])
        
        for j in range(1,k):
            formula.addClause([-x[(i)], -s[(i-1,j-1)], s[(i,j)]])
            formula.addClause([-s[(i-1,j)], s[(i,j)]])
        
        formula.addClause([-x[(i)], -s[(i-1,k-1)]])

    formula.addClause([-x[(n-1)], -s[(n-2,k-1)]])
    
    return VARINDEX, formula

def addExactlyKSeq(x, k, formula, VARINDEX):
    
    n = len(x)
    
    VARINDEX, formula = addAtMostKSeq(x, k, formula, VARINDEX)
    
    if k == 1:
        formula.addClause(x)    
    else:
        x = [-i for i in x]
    
        k = n - k

        VARINDEX, formula = addAtMostKSeq(x, k, formula, VARINDEX)
    
    return VARINDEX, formula

def hMerge(a, b, k, formula, VARINDEX):
    
    n = len(a)
    
    # Create the vars for output bits
    c = []
    for i in range(2*n):
        c.append(VARINDEX)
        VARINDEX += 1
    
    if n == 1:
        formula.addClause([a[(0)], b[(0)], -c[(0)]])
        formula.addClause([a[(0)], -c[(1)]])
        formula.addClause([b[(0)], -c[(1)]])
        
        # new
        formula.addClause([-a[(0)], c[(0)]])
        formula.addClause([-b[(0)], c[(0)]])
        formula.addClause([c[(1)], -a[(0)], -b[(0)]])
    
    elif n > 1:
        a_even = a[1::2]
        b_even = b[1::2]
        a_odd = a[::2]
        b_odd = b[::2]
        
        d, VARINDEX, formula = hMerge(a_odd, b_odd, k, formula, VARINDEX)
        e, VARINDEX, formula = hMerge(a_even, b_even, k, formula, VARINDEX)
        
        for i in range(n-1):
            formula.addClause([d[(i+1)], e[(i)], -c[(2*i + 1)]])
            formula.addClause([d[(i+1)], -c[(2*i+1 + 1)]])
            formula.addClause([e[(i)], -c[(2*i+1 + 1)]])
            
            #new
            formula.addClause([-d[(i+1)], c[(2*i + 1)]])
            formula.addClause([-e[(i)], c[(2*i + 1)]])
            formula.addClause([-e[(i)], -d[(i+1)], c[(2*i+1 + 1)]])
        
        c = [d[0]] + c[1:-1] + [e[len(e)-1]]
    
    return c, VARINDEX, formula

def sMerge(a, b, k, formula, VARINDEX):
    
    n = len(a)
    
    # Create the vars for output bits
    c = []
    for i in range(n+1):
        c.append(VARINDEX)
        VARINDEX += 1
    
    if n == 1:
        formula.addClause([a[(0)], b[(0)], -c[(0)]])
        formula.addClause([a[(0)], -c[(1)]])
        formula.addClause([b[(0)], -c[(1)]])
        
        # new
        formula.addClause([-a[(0)], c[(0)]])
        formula.addClause([-b[(0)], c[(0)]])
        formula.addClause([c[(1)], -a[(0)], -b[(0)]])
    
    elif n > 1:
        a_even = a[1::2]
        b_even = b[1::2]
        a_odd = a[::2]
        b_odd = b[::2]
        
        d, VARINDEX, formula = sMerge(a_odd, b_odd, k, formula, VARINDEX)
        e, VARINDEX, formula = sMerge(a_even, b_even, k, formula, VARINDEX)
        
        for i in range(n/2):
            formula.addClause([d[(i+1)], e[(i)], -c[(2*i + 1)]])
            formula.addClause([d[(i+1)], -c[(2*i+1 + 1)]])
            formula.addClause([e[(i)], -c[(2*i+1 + 1)]])
            
            #new
            formula.addClause([-d[(i+1)], c[(2*i + 1)]])
            formula.addClause([-e[(i)], c[(2*i + 1)]])
            formula.addClause([-e[(i)], -d[(i+1)], c[(2*i+1 + 1)]])
        
        c = [d[0]] + c[1:]
    
    return c, VARINDEX, formula

def hSort(a, k, formula, VARINDEX):
    
    n = len(a)/2
    c = []
    
    if 2*n == 2:
        c, VARINDEX, formula = hMerge([a[(0)]], [a[(1)]], k, formula, VARINDEX)
    elif 2*n > 2:
        d_1, VARINDEX, formula = hSort(a[:len(a)/2], k, formula, VARINDEX)
        d_2, VARINDEX, formula = hSort(a[len(a)/2:], k, formula, VARINDEX)
        c, VARINDEX, formula = hMerge(d_1, d_2, k, formula, VARINDEX)
    
    return c, VARINDEX, formula

def cardNetwork(a, k, formula, VARINDEX):
    
    n = len(a)
    c = []
    
    if k == n:
        c, VARINDEX, formula = hSort(a, k, formula, VARINDEX)
    elif n > k:
        d_1, VARINDEX, formula = cardNetwork(a[:k], k, formula, VARINDEX)
        d_2, VARINDEX, formula = cardNetwork(a[k:], k, formula, VARINDEX)
        c, VARINDEX, formula = sMerge(d_1, d_2, k, formula, VARINDEX)
    
    return c, VARINDEX, formula

def addCardNetworkBinaryActivation(x, p, formula, VARINDEX, z): # Asin 2011 encoding
    
    n = len(x)
    
    k = p
    
    if math.log(p,2) < math.ceil(math.log(p,2)):
        k = int(math.pow(2,int(math.ceil(math.log(p,2)))))
    
    m = 0
    if n % k > 0:
        m = k - n % k
    elif k > n:
        m = k - n
    
    # Create the vars for dummy inputs bits
    x_dummy = []
    for i in range(m):
        x_dummy.append(VARINDEX)
        formula.addClause([-x_dummy[(i)]])
        VARINDEX += 1
    
    x_extended = x + x_dummy

    c, VARINDEX, formula = cardNetwork(x_extended, k, formula, VARINDEX)
    
    formula.addClause([-z, c[(p-1)]])
    formula.addClause([z, -c[(p-1)]])
    
    return VARINDEX, formula

def get_args():
    
    import sys
    argv = sys.argv
    
    myargs = {}
    
    for index, arg in enumerate(argv):
        if arg[0] == '-':
            myargs[arg] = argv[index+1]

    return myargs

if __name__ == '__main__':
    
    import os
    myargs = get_args()
    
    setDomain = False
    setInstance = False
    setHorizon = False
    setObjective = False
    for arg in myargs:
        if arg == "-d":
            domain = myargs[(arg)]
            setDomain = True
        elif arg == "-i":
            instance = myargs[(arg)]
            setInstance = True
        elif arg == "-h":
            horizon = myargs[(arg)]
            setHorizon = True
        elif arg == "-o":
            optimize = myargs[(arg)]
            setObjective = True

    if setDomain and setInstance and setHorizon and setObjective:
        encode_fd_sat_plan(domain, instance, int(horizon), optimize)
        if optimize == "True":
            os.system("maxhs "+domain+"_"+instance+"_"+horizon+".wcnf > "+domain+"_"+instance+"_"+horizon+".output")
        else:
            os.system("./glucose-syrup-4.1/simp/glucose ./"+domain+"_"+instance+"_"+horizon+".cnf ./"+domain+"_"+instance+"_"+horizon+".output")
    elif not setDomain:
        print 'Domain is not provided.'
    elif not setInstance:
        print 'Instance is not provided.'
    elif not setHorizon:
        print 'Horizon is not provided.'
    else:
        print 'Optimization setting is not provided.'


    #encode_fd_sat_plan("navigation", "3x3", 4, "False")
    #encode_fd_sat_plan("navigation", "4x4", 5, "False")
    #encode_fd_sat_plan("navigation", "5x5", 8, "False")

    #encode_fd_sat_plan("inventory", "1", 7, "True")
    #encode_fd_sat_plan("inventory", "2", 8, "True")

    #encode_fd_sat_plan("sysadmin", "5", 4, "False")
