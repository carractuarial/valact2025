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
	for i := range len(array) {
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
	row, _ := reader.Read()

	for idx, val := range row {
		switch val {
		case "Issue_Age":
			age_col = idx
		case "Policy_Year":
			year_col = idx
		case "Rate":
			rate_col = idx
		}
	}

	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		file_age, _ = strconv.Atoi(row[age_col])
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

	for idx, val := range row {
		switch val {
		case "Issue_Age":
			age_col = idx
		case "Policy_Year":
			year_col = idx
		case "Rate":
			rate_col = idx
		case "Gender":
			gender_col = idx
		case "Risk_Class":
			class_col = idx
		}
	}

	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		file_age, _ = strconv.Atoi(row[age_col])
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
	for idx, val := range row {
		switch val {
		case "Attained_Age":
			age_col = idx
		case "Rate":
			rate_col = idx
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

func get_rates(gender string, risk_class string, issue_age int) map[string][120]float64 {
	var rates map[string][120]float64
	rates = make(map[string][120]float64)
	coi_rates := get_coi_rates(gender, risk_class, issue_age)
	per_unit_rates := get_per_unit_rates(issue_age)
	corridor_factors := get_corridor_factors(issue_age)
	premium_loads := create_array(0.06)
	policy_fees := create_array(120)
	naar_discount := create_array(math.Pow(1.01, -1/12.0))
	interest_rates := create_array(math.Pow(1.03, 1/12.0) - 1)

	rates["premium_load"] = premium_loads
	rates["policy_fee"] = policy_fees
	rates["per_unit"] = per_unit_rates
	rates["cf"] = corridor_factors
	rates["naar_disc"] = naar_discount
	rates["coi"] = coi_rates
	rates["interest"] = interest_rates
	
	return rates
}

func illustrate(rates map[string][120]float64, issue_age int, face_amount float64, annual_premium float64) float64 {
	maturity_age := 121
	projection_years := maturity_age - issue_age

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
		premium_load = premium * rates["premium_load"][policy_year-1]
		expense_charge = (rates["policy_fee"][policy_year-1] + rates["per_unit"][policy_year-1]*face_amount/1000) / 12.0
		av_for_db = start_value + premium - premium_load - expense_charge
		db = max(face_amount, rates["cf"][policy_year-1]*av_for_db)
		naar = max(0, db*rates["naar_disc"][policy_year-1]-max(0, av_for_db))
		coi = (naar / 1000.0) * (rates["coi"][policy_year-1] / 12)
		av_for_interest = av_for_db - coi
		interest = max(0, av_for_interest) * rates["interest"][policy_year-1]
		end_value = av_for_interest + interest
	}

	return end_value
}

func solve(rates map[string][120]float64, issue_age int, face_amount float64) float64 {
	guess_lo := 0.0
	guess_hi := face_amount / 100.0

	for {
		end_value := illustrate(rates, issue_age, face_amount, guess_hi)
		if end_value <= 0 {
			guess_lo = guess_hi
			guess_hi *= 2
		} else {
			break
		}
	}

	guess_md := 0.0
	for ; (guess_hi - guess_lo) > 0.005; {
		guess_md = (guess_lo + guess_hi) / 2.0
		end_value := illustrate(rates, issue_age, face_amount, guess_md)
		if end_value <= 0 {
			guess_lo = guess_md
		} else {
			guess_hi = guess_md
		}
	}

	result := math.Round(guess_md * 100.0) / 100.0
	end_value := illustrate(rates, issue_age, face_amount, result)
	if end_value <= 0 {result += 0.01}
	return result
}

func single() {
	issue_age := 35
	gender := "M"
	risk_class := "NS"
	face_amount := 100000.0
	//premium := 1255.03
	x := 0.0

	fmt.Println("Starting...")
	start := time.Now()
	iter := 1000
	//rates := get_rates(gender, risk_class, issue_age)
	for i := 0; i < iter; i++ {
		rates := get_rates(gender, risk_class, issue_age)
		//x = illustrate(rates, issue_age, face_amount, premium)
		x = solve(rates, issue_age, face_amount)
	}
	end := time.Now()
	fmt.Println("Ending...")
	elapsed := end.Sub(start)
	fmt.Println("Prem", x)
	fmt.Println("Total time", elapsed)
	fmt.Println("Runs", iter)
	fmt.Println("Per iteration", float64(elapsed)/float64(iter))
}

func worker(id int, jobs <-chan int, results chan<- float64) {
	gender := "M"
	risk_class := "NS"
	issue_age := 35
	rates := get_rates(gender, risk_class, issue_age)	
	for _ = range jobs {
		
		face_amount := 100000.0
		premium := 1255.03
		result := 0.0
		
		result = illustrate(rates, issue_age, face_amount, premium)
		//result = solve(rates, issue_age, face_amount)
		results <- result
	}
}

func multi() {
	fmt.Println("Starting...")
	start := time.Now()
	numWorkers := 8
	numJobs := 1000
	jobs := make(chan int, numJobs)
	results := make(chan float64, numJobs)

	for i :=1; i <= numWorkers; i++ {
		go worker(i, jobs, results)
	}

	for i := 1; i <= numJobs; i++ {
		jobs <- i
	}
	close(jobs)
	var result float64
	for i := 1; i <= numJobs; i++ {
		result = <- results	
	}
	end := time.Now()
	fmt.Println("Ending...")
	elapsed := end.Sub(start)
	fmt.Println("Prem", result)
	fmt.Println("Total time", elapsed)
	fmt.Println("Runs", numJobs)
	fmt.Println("Per iteration", float64(elapsed)/float64(numJobs))
}

func main() {
	//single()
	multi()
}
