// DAOGuillotine JavaScript SDK Client
import { createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';

const CONTRACT_ADDRESS = "0x2382aD12494199b7ABD97D4453c6CB69afD9dF15";

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
