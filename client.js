// DAOGuillotine JavaScript SDK Client
import { createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';

const CONTRACT_ADDRESS = "0x0Be97369B3a37a246cE0666e4728E51Cb0877cee";

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
