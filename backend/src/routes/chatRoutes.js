const express=require('express');
const chatRouter=express.Router();
const {handleChat}=require("../controllers/chatController");

chatRouter.post("/query",handleChat);

module.exports={chatRouter};