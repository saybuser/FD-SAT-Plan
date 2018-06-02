# FD_SAT_Plan

Factored Deep SAT Planner (FD-SAT-Plan) [1] is a two-stage planner that (i) learns the state transition function of a factored [2] planning problem using Binarized Neural Networks [3] from data, and (ii) compiles the sequence of learned transition functions into CNF and solve it using off-the-shelf SAT solver [4].

## References
[1] Buser Say, Scott Sanner. Planning in Factored State and Action Spaces with Learned Binarized Neural Network Transition Models. IJCAI 2018.
[2] Craig Boutilier, Thomas Dean, and Steve Hanks. Decision-theoretic planning: Structural assumptions and computational leverage. JAIR, 11(1):1–94, 1999.
[3] Itay Hubara, Matthieu Courbariaux, Daniel Soudry, Ran El-Yaniv, and Yoshua Bengio. Binarized neural networks. In 29th NIPS, pages 4107–4115. Curran Associates, Inc., 2016.
[4] Gilles Audemard and Laurent Simon. Lazy Clause Exchange Policy for Parallel SAT Solvers, pages 197–205. Springer Int. Publishing, 2014.
