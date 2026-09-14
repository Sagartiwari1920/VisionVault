require('dotenv').config();
const express=require('express');
const app=express();
const {initializeMinio} =require("./src/config/minio");
const {connectRabbitMQ}=require("./src/config/rabbitmq");
const {documentRouter}=require("./src/routes/documentRoutes");
const {chatRouter}=require("./src/routes/chatRoutes");

app.use(express.json());

app.use("/input",documentRouter);
app.use("/input/chat",chatRouter);

app.use('/',(req,res)=>{
    res.send("Hey sagar");
})

const PORT=process.env.PORT || 8888;
async function connections(){ 
   try {
    //connect to min io 
    initializeMinio();
    //connect to rabbitmq
    connectRabbitMQ();
     app.listen(PORT,()=>{
        console.log(`Server is running at port ${PORT}`);
    })
    
   } catch (err) {
    console.log(err.message);
   }
}
connections();
 