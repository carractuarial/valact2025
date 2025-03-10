import abc
from dataclasses import dataclass
import math

import polars as pl


@dataclass
class Insured:
    """
    Simple data structure for an insured to house characteristics

    Parameters/Attributes
    ---------------------
    gender: str
        Gender of insured
    risk_class: str
        Risk class of insured
    issue_age: int
        Issue age of insured
    """
    gender: str
    risk_class: str
    issue_age: int


class Rates:
    """
    Container for illustration rates

    Can access each rate by policy year
    """

    def __init__(self,
                 premium_loads: list[float],
                 policy_fees: list[float],
                 per_units: list[float],
                 corridor_factors: list[float],
                 naar_discs: list[float],
                 cois: list[float],
                 interest_rates: list[float]):
        self._premium_loads = premium_loads
        self._policy_fees = policy_fees
        self._per_units = per_units
        self._corridor_factors = corridor_factors
        self._naar_discs = naar_discs
        self._cois = cois
        self._interest_rates = interest_rates

    def premium_load(self, policy_year: int) -> float:
        """
        Retrieve premium load by policy year

        Parameters
        ----------
        policy_year: int
            Policy year to retrieve rate for

        Returns
        -------
        float
            Premium load
        """
        return self._premium_loads[policy_year - 1]

    def policy_fee(self, policy_year: int) -> float:
        """
        Retrieve policy fee by policy year

        Parameters
        ----------
        policy_year: int
            Policy year to retrieve rate for

        Returns
        -------
        float
            Policy fee
        """
        return self._policy_fees[policy_year - 1]

    def per_unit(self, policy_year: int) -> float:
        """
        Retrieve per unit load by policy year

        Parameters
        ----------
        policy_year: int
            Policy year to retrieve rate for

        Returns
        -------
        float
            Per unit load
        """
        return self._per_units[policy_year - 1]

    def corridor_factor(self, policy_year: int) -> float:
        """
        Retrieve corridor factor by policy year

        Parameters
        ----------
        policy_year: int
            Policy year to retrieve rate for

        Returns
        -------
        float
            Corridor factor
        """
        return self._corridor_factors[policy_year - 1]

    def naar_disc(self, policy_year: int) -> float:
        """
        Retrieve NAAR discount factor by policy year

        Parameters
        ----------
        policy_year: int
            Policy year to retrieve rate for

        Returns
        -------
        float
            NAAR discount factor
        """
        return self._naar_discs[policy_year - 1]

    def coi(self, policy_year: int) -> float:
        """
        Retrieve COI rate by policy year

        Parameters
        ----------
        policy_year: int
            Policy year to retrieve rate for

        Returns
        -------
        float
            COI rate
        """
        return self._cois[policy_year - 1]

    def interest_rate(self, policy_year: int) -> float:
        """
        Retrieve interest rate by policy year

        Parameters
        ----------
        policy_year: int
            Policy year to retrieve rate for

        Returns
        -------
        float
            Interest rate
        """
        return self._interest_rates[policy_year - 1]


class UniversalLifeProduct(abc.ABC):
    """
    Abstract base class for Universal Life products

    Must be subclassed and methods overwritten

    Attributes
    ----------
    maturity_age: int
        (class attribute) maturity age of product
    """
    maturity_age = 121

    @staticmethod
    @abc.abstractmethod
    def product_rates_for_policy(insured: Insured) -> Rates:
        """
        Class method to retrieve product rates for particular insured
        Must be overriden by subclass

        Parameters
        ----------
        insured: Insured
            Insured containing characteristics to retrieve rates for

        Returns
        -------
        Rates
            Illustration rates for given Insured's characteristics
        """
        pass

    @classmethod
    @abc.abstractmethod
    def at_issue_illustration(cls, rates: Rates, issue_age: int, face_amount: int, annual_premium: float) -> dict[str, list[int | float]]:
        """
        Method to generate at issue illustration based on provided parameters

        Must be overriden by subclasses

        Parameters
        ----------
        rates: Rates
            Rates to use in illustration
        issue_age: int
            Issue age for use in illustration
        face_amount: int
            Face amount for illustration
        annual_premium: float
            Premium to be paid annually in illustration

        Returns
        -------
        dict[str, list[int | float]]
            Illustration as a dictionary
        """
        pass

    @classmethod
    def solve_minimum_premium_to_maturity(cls, rates: Rates, issue_age: int, face_amount: int) -> dict[str, list[int | float]]:
        guess_lo = 0
        guess_hi = face_amount / 100

        while True:
            illustration = cls.at_issue_illustration(
                rates, issue_age, face_amount, guess_hi)
            if illustration['Value_End'][-1] <= 0:
                guess_lo = guess_hi
                guess_hi *= 2
            else:
                break

        while (guess_hi - guess_lo > 0.005):
            guess_md = (guess_lo + guess_hi) / 2
            illustration = cls.at_issue_illustration(
                rates, issue_age, face_amount, guess_md)
            if illustration['Value_End'][-1] <= 0:
                guess_lo = guess_md
            else:
                guess_hi = guess_md

        result = round(guess_md, 2)
        illustration = cls.at_issue_illustration(
            rates, issue_age, face_amount, guess_md)
        if illustration['Value_End'][-1] <= 0:
            result += 0.01

        return result


class Product1(UniversalLifeProduct):
    maturity_age = 121

    @classmethod
    def _get_per_unit_rates(cls, issue_age: int) -> list[float]:
        """
        Retrieve per $1,000 of face amount rates from a CSV
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
        rates = [0.0 for _ in range(
            cls.maturity_age - issue_age)]  # create default array
        df = pl.scan_csv('unit_load.csv').filter(
            pl.col('Issue_Age') == issue_age).collect()  # load filtered csv
        for i in range(len(df)):
            rates[df['Policy_Year'][i]-1] = df['Rate'][i]  # update array
        return rates

    @classmethod
    def _get_coi_rates(cls, gender: str, risk_class: str, issue_age: int) -> list[float]:
        """
        Retrieve per $1,000 COI rates from a CSV that varies by 
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
        rates = [0.0 for _ in range(
            cls.maturity_age - issue_age)]
        df = pl.scan_csv('coi.csv').filter(pl.col('Gender') == gender, pl.col(
            'Risk_Class') == risk_class, pl.col('Issue_Age') == issue_age).collect()
        for i in range(len(df)):
            rates[df['Policy_Year'][i]-1] = df['Rate'][i]
        return rates

    @classmethod
    def _get_corridor_factors(cls, issue_age: int) -> list[float]:
        """
        Retrieve corridor factors from a CSV that varies by attained age

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
        years = cls.maturity_age - issue_age
        rates = [1.0 for _ in range(
            years)]
        df = pl.scan_csv('corridor_factors.csv').filter(
            pl.col('Attained_Age') >= issue_age).collect()
        for i in range(min(years, len(df))):
            rates[df['Attained_Age'][i]-issue_age] = df['Rate'][i]
        return rates

    @classmethod
    def product_rates_for_policy(cls, insured: Insured) -> dict[str, list[float]]:
        years = cls.maturity_age - insured.issue_age
        premium_loads = [0.06 for _ in range(years)]
        policy_fees = [120 for _ in range(years)]
        unit_loads = cls._get_per_unit_rates(insured.issue_age)
        corridor_factors = cls._get_corridor_factors(
            insured.issue_age)
        naar_discs = [1.01**(-1/12) for _ in range(years)]
        cois = cls._get_coi_rates(
            insured.gender, insured.risk_class, insured.issue_age)
        interest_rates = [1.03**(1/12)-1 for _ in range(years)]

        rates = Rates(premium_loads,
                      policy_fees,
                      unit_loads,
                      corridor_factors,
                      naar_discs,
                      cois,
                      interest_rates)

        return rates

    @classmethod
    def at_issue_illustration(cls, rates: Rates, issue_age: int, face_amount: int, annual_premium: float) -> dict[str, list[int | float]]:
        projection_years = cls.maturity_age - issue_age
        fields = ['Policy_Month',
                  'Policy_Year',
                  'Month_In_Policy_Year',
                  'Value_Start',
                  'Premium',
                  'Premium_Load',
                  'Expense_Charge',
                  'Value_For_DB',
                  'Death_Benefit',
                  'NAAR',
                  'COI_Charge',
                  'Interest',
                  'Value_End']
        output = {field: [0 for _ in range(
            12*projection_years)] for field in fields}
        end_value = 0
        policy_year = 0
        for i in range(12*projection_years):
            policy_year += 1 if (i % 12 == 0) else 0
            start_value = end_value
            premium = annual_premium if (i % 12 == 0) else 0
            premium_load = premium * rates.premium_load(policy_year)
            expense_charge = (rates.policy_fee(policy_year) +
                              rates.per_unit(policy_year) * face_amount / 1000) / 12
            av_for_db = start_value + premium - premium_load - expense_charge
            db = max(face_amount, av_for_db *
                     rates.corridor_factor(policy_year))
            naar = max(0, db * rates.naar_disc(policy_year) -
                       max(0, av_for_db))
            coi = (naar / 1000) * (rates.coi(policy_year) / 12)
            av_for_interest = av_for_db - coi
            interest = max(0, av_for_interest) * \
                rates.interest_rate(policy_year)
            end_value = av_for_interest + interest

            # update illustration values
            output['Policy_Month'][i] = i+1
            output['Policy_Year'][i] = policy_year
            output['Month_In_Policy_Year'][i] = (i % 12) + 1
            output['Value_Start'][i] = start_value
            output['Premium'][i] = premium
            output['Premium_Load'][i] = premium_load
            output['Expense_Charge'][i] = expense_charge
            output['Value_For_DB'][i] = av_for_db
            output['Death_Benefit'][i] = db
            output['NAAR'][i] = naar
            output['COI_Charge'][i] = coi
            output['Interest'][i] = interest
            output['Value_End'][i] = end_value

            if end_value < 0:
                # print('WARNING: Policy lapses before maturity')
                return output
        return output


class UniversalLifePolicy:

    def __init__(self, insured: Insured, product: UniversalLifeProduct, face_amount: int):
        self.insured = insured
        self.product = product
        self.face_amount = face_amount
        self.rates = product.product_rates_for_policy(insured)

    @property
    def issue_age(self):
        return self.insured.issue_age

    def at_issue_illustration(self, annual_premium: float):
        return self.product.at_issue_illustration(self.rates, self.issue_age, self.face_amount, annual_premium)

    def solve_minimum_premium_to_maturity(self):
        return self.product.solve_minimum_premium_to_maturity(self.rates, self.issue_age, self.face_amount)


if __name__ == '__main__':
    ins = Insured("M", "NS", 35)
    pol = UniversalLifePolicy(ins, Product1, 100000)
    print(pol.at_issue_illustration(1255.03))
