import dns from 'dns';
import mongoose from 'mongoose';

export default async function connectDB() {
  // Some networks block SRV lookups; use public DNS if DNS_SERVERS is set
  if (process.env.DNS_SERVERS) {
    dns.setServers(process.env.DNS_SERVERS.split(','));
  }
  const uri = process.env.MONGO_URI || 'mongodb://localhost:27017/cctv_parking';
  await mongoose.connect(uri);
  console.log('MongoDB connected');
}