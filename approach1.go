package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"math"
	"os"
	"strconv"
	"time"
)

func create_array(value float64) [120]float64 {
	var array [120]float64
	for i := 0; i < len(array); i++ {
		array[i] = value
	}
	return array
}

func get_per_unit_rates(issue_age int) [120]float64 {
	// create default output
	rates := create_array(0)

	// create variables outside of loops
	var age_col, year_col, rate_col int
	var file_age, file_year int
	var file_rate float64

	// open file
	file, err := os.Open("unit_load.csv")
	if err != nil {
		log.Fatal("Error while reading the file", err)
	}

	defer file.Close()
	reader := csv.NewReader(file)
	row, err := reader.Read()

	for i := 0; i < len(row); i++ {
		switch row[i] {
		case "Issue_Age":
			age_col = i
		case "Policy_Year":
			year_col = i
		case "Rate":
			rate_col = i
		}
	}

	for {
		row, err := reader.Read()
		//fmt.Println(row)
		if err == io.EOF {
			break
		}
		file_age, err = strconv.Atoi(row[age_col])
		if file_age == issue_age {
			file_rate, _ = strconv.ParseFloat(row[rate_col], 64)
			file_year, _ = strconv.Atoi(row[year_col])
			rates[file_year-1] = file_rate
		}
	}
	return rates
}

func get_coi_rates(gender string, risk_class string, issue_age int) [120]float64 {
	// create array
	rates := create_array(0)

	// create variables outside of loops
	var age_col, year_col, rate_col, gender_col, class_col int
	var file_age, file_year int
	var file_rate float64

	// open file
	file, err := os.Open("coi.csv")
	if err != nil {
		log.Fatal("Error while reading the file", err)
	}

	defer file.Close()
	reader := csv.NewReader(file)
	row, _ := reader.Read()

	for i := 0; i < len(row); i++ {
		switch row[i] {
		case "Issue_Age":
			age_col = i
		case "Policy_Year":
			year_col = i
		case "Rate":
			rate_col = i
		case "Gender":
			gender_col = i
		case "Risk_Class":
			class_col = i
		}
	}

	for {
		row, err := reader.Read()
		//fmt.Println(row)
		if err == io.EOF {
			break
		}
		file_age, err = strconv.Atoi(row[age_col])
		if file_age == issue_age && row[gender_col] == gender && row[class_col] == risk_class {
			file_rate, _ = strconv.ParseFloat(row[rate_col], 64)
			file_year, _ = strconv.Atoi(row[year_col])
			rates[file_year-1] = file_rate
		}
	}
	return rates
}

func get_corridor_factors(issue_age int) [120]float64 {
	rates := create_array(1.0)
	var age_col, rate_col int

	file, err := os.Open("corridor_factors.csv")
	if err != nil {
		log.Fatal("Error when opening file", err)
	}

	defer file.Close()
	reader := csv.NewReader(file)
	row, _ := reader.Read()
	for i := 0; i < len(row); i++ {
		switch row[i] {
		case "Attained_Age":
			age_col = i
		case "Rate":
			rate_col = i
		}
	}

	var file_age int
	var file_rate float64
	for {
		row, err = reader.Read()
		if err == io.EOF {
			break
		}
		file_age, _ = strconv.Atoi(row[age_col])
		if file_age >= issue_age {
			file_rate, _ = strconv.ParseFloat(row[rate_col], 64)
			rates[file_age-issue_age] = file_rate
		}
	}
	return rates
}

func illustrate(gender string, risk_class string, issue_age int, face_amount float64, annual_premium float64) float64 {

	maturity_age := 121
	projection_years := maturity_age - issue_age

	coi_rates := get_coi_rates(gender, risk_class, issue_age)
	per_unit_rates := get_per_unit_rates(issue_age)
	corridor_factors := get_corridor_factors(issue_age)
	premium_loads := create_array(0.06)
	policy_fees := create_array(120)
	naar_discount := create_array(math.Pow(1.01, -1/12.0))
	interest_rate := create_array(math.Pow(1.03, 1/12.0) - 1)

	//fmt.Println(naar_discount)
	//fmt.Println(interest_rate)

	end_value := 0.0
	policy_year := 0
	var start_value, premium, premium_load, expense_charge, av_for_db, db, naar, coi, av_for_interest, interest float64
	for i := 1; i <= 12*projection_years; i++ {
		if (i % 12) == 1 {
			policy_year += 1
			premium = annual_premium
		} else {
			premium = 0.0
		}
		start_value = end_value
		premium_load = premium * premium_loads[policy_year-1]
		expense_charge = (policy_fees[policy_year-1] + per_unit_rates[policy_year-1]*face_amount/1000) / 12.0
		av_for_db = start_value + premium - premium_load - expense_charge
		db = max(face_amount, corridor_factors[policy_year-1]*av_for_db)
		naar = max(0, db*naar_discount[policy_year-1]-max(0, av_for_db))
		coi = (naar / 1000.0) * (coi_rates[policy_year-1] / 12)
		av_for_interest = av_for_db - coi
		interest = max(0, av_for_interest) * interest_rate[policy_year-1]
		end_value = av_for_interest + interest
	}

	return end_value
}

func main() {
	issue_age := 35
	gender := "M"
	risk_class := "NS"

	//var unit_rates [120]float64
	//var coi_rates [120]float64
	//var cf_rates [120]float64

	//unit_rates = get_per_unit_rates(issue_age)
	//coi_rates = get_coi_rates(gender, risk_class, issue_age)
	//cf_rates = get_corridor_factors(issue_age)

	//fmt.Println("Unit rates", unit_rates)
	//fmt.Println("COI rates", coi_rates)
	//fmt.Println("Corridor factors", cf_rates)

	//fmt.Println(illustrate(gender, risk_class, issue_age, 100000, 1255.03))
	fmt.Println("Starting...")
	start := time.Now()
	iter := 1000
	for i := 0; i < iter; i++ {
		illustrate(gender, risk_class, issue_age, 100000, 1255.03)
	}
	end := time.Now()
	fmt.Println("Ending...")
	elapsed := end.Sub(start)
	fmt.Println("Total time", elapsed)
	fmt.Println("Runs", iter)
	fmt.Println("Per iteration", float64(elapsed)/float64(iter))
}
