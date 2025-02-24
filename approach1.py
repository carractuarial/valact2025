import polars as pl


def get_per_unit_rates(issue_age: int) -> list[float]:
    """
    Function to retrieve per $1,000 of face amount rates from a CSV
    that varies by issue age and policy year

    Parameters
    ----------
    issue_age: int
        The issue age to retrieve

    Returns
    -------
    list[float]
        List of rates where index 0 is for policy year 1; default entry for
        each index is 0
    """
    rates = [0.0 for _ in range(120)]           # create default array
    df = pl.scan_csv('unit_load.csv').filter(
        pl.col('Issue_Age') == issue_age).collect()  # load filtered csv
    for i in range(len(df)):
        rates[df['Policy_Year'][i]-1] = df['Rate'][i]  # update array
    return rates


def get_coi_rates(gender: str, risk_class: str, issue_age: int) -> list[float]:
    """
    Function to retrieve per $1,000 COI rates from a CSV that varies by 
    gender, risk class, issue age, and policy year

    Parameters
    ----------
    gender: str
        Gender of insured, M or F expected
    risk_class: str
        Risk class of insured, NS or SM expected
    issue_age: int
        Issue age of insured

    Returns
    -------
    list[float]
        List of rates where index 0 is for policy year 1; default entry for
        each index is 0
    """
    rates = [0.0 for _ in range(120)]
    df = pl.scan_csv('coi.csv').filter(pl.col('Issue_Age') == issue_age, pl.col(
        'Gender') == gender, pl.col('Risk_Class') == risk_class).collect()
    for i in range(len(df)):
        rates[df['Policy_Year'][i]-1] = df['Rate'][i]
    return rates


def get_corridor_factors(issue_age: int) -> list[float]:
    """
    Function to retrieve corridor factors from a CSV that varies by attained
    age

    Parameters
    ----------
    issue_age: int
        Issue age of insured

    Returns
    -------
    list[float]
        List of factors by policy year, index 0 is for policy year 1; default values
        of 1 are used if rates not found
    """
    rates = [1.0 for _ in range(120)]
    df = pl.scan_csv('corridor_factors.csv').filter(
        pl.col('Attained_Age') >= issue_age).collect()
    for i in range(len(df)):
        rates[df['Attained_Age'][i]-issue_age] = df['Rate'][i]
    return rates


def illustrate(gender: str, risk_class: str, issue_age: int, face_amount: int, annual_premium: float) -> dict[str, list[int | float]]:
    """
    Generate an at issue illustration for given case

    Parameters
    ----------
    gender: str
        Gender of insured for policy illustration, expected M or F
    risk_class: str
        Risk class of insured for policy illustration, expects NS or SM
    issue_age: int
        Issue age of insured for policy illustration
    face_amount: int
        Face amount for policy illustration
    annual_premium: float
        Annual premium

    Returns
    -------
    dict[str,list[int|float]]
        Illustrated values where keys are columns and resulting values 
        are lists
    """
    maturity_age = 121
    projection_years = maturity_age - issue_age
    fields = ['Policy_Month',
              'Policy_Year',
              'Month_In_Policy_Year',
              'Value_Start',
              'Premium',
              'Premium_Load',
              'Expense_Charge',
              'Death_Benefit',
              'NAAR',
              'COI_Charge',
              'Interest',
              'Value_End']
    output = {field: [0 for _ in range(12*projection_years)]
              for field in fields}

    prem_load_rate = 0.06
    policy_fee_rate = 120
    per_unit_rates = get_per_unit_rates(issue_age)
    corridor_factors = get_corridor_factors(issue_age)
    naar_discount = 1.01**(-1/12)
    coi_rates = get_coi_rates(gender, risk_class, issue_age)
    interest_rate = (1.03**(1/12) - 1)

    end_value = 0
    policy_year = 0
    for i in range(12*projection_years):
        policy_year += 1 if (i % 12 == 0) else 0
        start_value = end_value
        premium = annual_premium if (i % 12 == 0) else 0
        premium_load = prem_load_rate * premium
        expense_charge = (
            policy_fee_rate + per_unit_rates[policy_year-1] * face_amount / 1000) / 12
        av_for_db = start_value + premium - premium_load - expense_charge
        db = max(face_amount, corridor_factors[policy_year-1] * av_for_db)
        naar = max(0, db * naar_discount - max(0, av_for_db))
        coi = (naar / 1000) * (coi_rates[policy_year-1] / 12)
        av_for_interest = av_for_db - coi
        interest = max(0, av_for_interest) * interest_rate
        end_value = av_for_interest + interest

        output['Policy_Month'][i] = i+1
        output['Policy_Year'][i] = policy_year
        output['Month_In_Policy_Year'][i] = ((i-1) % 12) + 1
        output['Value_Start'][i] = start_value
        output['Premium'][i] = premium
        output['Premium_Load'][i] = premium_load
        output['Expense_Charge'][i] = expense_charge
        output['Death_Benefit'][i] = db
        output['NAAR'][i] = naar
        output['COI_Charge'][i] = coi
        output['Interest'][i] = interest
        output['Value_End'][i] = end_value

        # exit early if lapse before end
        if end_value < 0:
            # print('Warning: policy lapsed prior to maturity')
            return output

    # if successful, exit with desired information
    return output


def solve_for_premium(gender: str, risk_class: str, issue_age: int, face_amount: int) -> dict[str, list[int | float]]:
    guess_lo = 0
    guess_hi = face_amount / 100

    while True:
        illus = illustrate(gender, risk_class, issue_age,
                           face_amount, guess_hi)
        if illus['Value_End'][-1] <= 0:
            guess_lo = guess_hi
            guess_hi = guess_hi * 2
        else:
            break

    while (guess_hi - guess_lo) > 0.005:
        guess_md = (guess_lo + guess_hi)/2
        illus = illustrate(gender, risk_class, issue_age,
                           face_amount, guess_md)
        if illus['Value_End'][-1] <= 0:
            guess_lo = guess_md
        else:
            guess_hi = guess_md

    result = round(guess_md, 2)
    illus = illustrate(gender, risk_class, issue_age, face_amount, guess_md)
    if illus['Value_End'][-1] <= 0:
        result += 0.01

    return result


if __name__ == '__main__':
    result = illustrate("M", "NS", 35, 100000, 1255.03)
    print(result)
