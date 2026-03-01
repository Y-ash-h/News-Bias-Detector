import axios from 'axios';

const websites = [
    "https://www.ndtv.com/",
    "https://www.thequint.com/",
    "https://www.hindustantimes.com/",
    "https://www.opindia.com/",
    "https://timesofindia.indiatimes.com/",
    "https://www.republicworld.com/",
]

const backendUrl = process.env.BACKEND_URL || "http://localhost:5001"
const nextBackend = "/api/"
const payload = {
    websites: websites,
    count: 60000,
}

const getCachedData = async () => {
    const response = await axios.get(
        `${nextBackend}cache`,
    );
    return response.data;
};

const getNewsArticles = async () => {    
    const response = await axios.post(
        backendUrl + "scaper",
        payload,
        {
            headers: {
                "Content-Type": "application/json",
            },
        }
    );
}


const scrapeScrapy = async () => {
    const response = await axios.post(
        backendUrl + "get-scrape",
        payload,
        {
            headers: {
                "Content-Type": "application/json",
            },
        }
    )
    return response.data.results;
}

export { getNewsArticles, getCachedData, scrapeScrapy, backendUrl, nextBackend, payload, websites };