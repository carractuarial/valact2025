import cProfile
import timeit

import approach1
import approach2


def test(header, code, setup, n):
    print(f'\n{header}')
    t = timeit.Timer(code, setup=setup)
    print(f"{n} calls:", t.timeit(number=n))

    many = t.repeat(number=n)
    print(f"\n{n} calls\n5 repeats:", many, "\nAvg:", sum(many)/len(many))
    # cProfile.run(code, sort='tottime')


if __name__ == '__main__':
    n = 1000
    header1 = "ILLUSTRATIONS-----------------------------"
    header2 = "SOLVES------------------------------------"
    print('\n------------RUNNING APPROACH 1------------')

    code = "approach1.illustrate('M','NS',35,100000,1255.03)"
    setup = "import approach1"
    # test(header1, code, setup, n)

    code = "approach1.solve_for_premium('M','NS',35,100000)"
    # test(header2, code, setup, n)

    print('\n------------RUNNING APPROACH 2------------')
    setup = "import approach2"
    code = 'ins = approach2.Insured("M", "NS", 35)\n'
    code += 'prod = approach2.Product1\n'
    code += 'pol = approach2.UniversalLifePolicy(ins, prod, 100000)\n'
    code += 'pol.at_issue_illustration(1255.03)'
    test(header1, code, setup, n)

    code = 'ins = approach2.Insured("M", "NS", 35)\n'
    code += 'prod = approach2.Product1\n'
    code += 'pol = approach2.UniversalLifePolicy(ins, prod, 100000)\n'
    code += 'pol.solve_minimum_premium_to_maturity()'
    test(header2, code, setup, n)
