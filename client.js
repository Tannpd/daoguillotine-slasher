// DAOGuillotine JavaScript SDK Client
import { createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';

const CONTRACT_ADDRESS = "0x4b9bAb2d12B6003206Fb7DFB06fB8a81B482B41b";

export async function getPayrollsCount() {
  const client = createClient({ chain: studionet });
  const count = await client.readContract({
    address: CONTRACT_ADDRESS,
    functionName: "get_payrolls_count",
    args: []
  });
  return Number(count);
}

export async function getPayroll(payrollId) {
  const client = createClient({ chain: studionet });
  const payrollJsonStr = await client.readContract({
    address: CONTRACT_ADDRESS,
    functionName: "get_payroll",
    args: [payrollId]
  });
  return JSON.parse(payrollJsonStr);
}
