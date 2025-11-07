import api from "./api";

export const getTransactions = async (filters = {}) => {
    const res = await api.get("/transactions", {params: filters});
    return res.data;
}

export const createTransaction = async (data) => {
    const res = await api.post("/transactions", data);
    return res.data;
}