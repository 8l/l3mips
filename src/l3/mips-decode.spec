---------------------------------------------------------------------------
-- Model of the 64-bit MIPS ISA (MIPS III with some extra instructions)
-- (c) Anthony Fox, University of Cambridge
---------------------------------------------------------------------------

--================================================
-- Instruction decoding
--================================================

instruction Decode (w::word) =
{
   match w
   {
      case '000 000 00000 rt rd imm5 000 000' => Shift (SLL (rt, rd, imm5))
      case '000 000 00000 rt rd imm5 000 010' => Shift (SRL (rt, rd, imm5))
      case '000 000 00000 rt rd imm5 000 011' => Shift (SRA (rt, rd, imm5))
      case '000 000 rs rt rd 00000 000 100' => Shift (SLLV (rs, rt, rd))
      case '000 000 rs rt rd 00000 000 110' => Shift (SRLV (rs, rt, rd))
      case '000 000 rs rt rd 00000 000 111' => Shift (SRAV (rs, rt, rd))
      case '000 000 rs 00000 00000 hint 001 000' => Branch (JR (rs))
      case '000 000 rs 00000 rd hint 001 001' => Branch (JALR (rs, rd))
      case '000 000 rs rt rd 00000 001 010' => ArithR (MOVZ (rs, rt, rd))
      case '000 000 rs rt rd 00000 001 011' => ArithR (MOVN (rs, rt, rd))
      case '000 000 00000 code 001 100' => SYSCALL
      case '000 000 00000 code 001 101' => BREAK
      case '000 000 00000 00000 00000 imm5 001 111' => SYNC (imm5)
      case '000 000 00000 00000 rd 00000 010 000' => MultDiv (MFHI (rd))
      case '000 000 rs 00000 00000 00000 010 001' => MultDiv (MTHI (rs))
      case '000 000 00000 00000 rd 00000 010 010' => MultDiv (MFLO (rd))
      case '000 000 rs 00000 00000 00000 010 011' => MultDiv (MTLO (rs))
      case '000 000 rs rt rd 00000 010 100' => Shift (DSLLV (rs, rt, rd))
      case '000 000 rs rt rd 00000 010 110' => Shift (DSRLV (rs, rt, rd))
      case '000 000 rs rt rd 00000 010 111' => Shift (DSRAV (rs, rt, rd))
      case '000 000 rs rt 00000 00000 011 000' => MultDiv (MULT (rs, rt))
      case '000 000 rs rt 00000 00000 011 001' => MultDiv (MULTU (rs, rt))
      case '000 000 rs rt 00000 00000 011 010' => MultDiv (DIV (rs, rt))
      case '000 000 rs rt 00000 00000 011 011' => MultDiv (DIVU (rs, rt))
      case '000 000 rs rt 00000 00000 011 100' => MultDiv (DMULT (rs, rt))
      case '000 000 rs rt 00000 00000 011 101' => MultDiv (DMULTU (rs, rt))
      case '000 000 rs rt 00000 00000 011 110' => MultDiv (DDIV (rs, rt))
      case '000 000 rs rt 00000 00000 011 111' => MultDiv (DDIVU (rs, rt))
      case '000 000 rs rt rd 00000 100 000' => ArithR (ADD (rs, rt, rd))
      case '000 000 rs rt rd 00000 100 001' => ArithR (ADDU (rs, rt, rd))
      case '000 000 rs rt rd 00000 100 010' => ArithR (SUB (rs, rt, rd))
      case '000 000 rs rt rd 00000 100 011' => ArithR (SUBU (rs, rt, rd))
      case '000 000 rs rt rd 00000 100 100' => ArithR (AND (rs, rt, rd))
      case '000 000 rs rt rd 00000 100 101' => ArithR (OR (rs, rt, rd))
      case '000 000 rs rt rd 00000 100 110' => ArithR (XOR (rs, rt, rd))
      case '000 000 rs rt rd 00000 100 111' => ArithR (NOR (rs, rt, rd))
      case '000 000 rs rt rd 00000 101 010' => ArithR (SLT (rs, rt, rd))
      case '000 000 rs rt rd 00000 101 011' => ArithR (SLTU (rs, rt, rd))
      case '000 000 rs rt rd 00000 101 100' => ArithR (DADD (rs, rt, rd))
      case '000 000 rs rt rd 00000 101 101' => ArithR (DADDU (rs, rt, rd))
      case '000 000 rs rt rd 00000 101 110' => ArithR (DSUB (rs, rt, rd))
      case '000 000 rs rt rd 00000 101 111' => ArithR (DSUBU (rs, rt, rd))
      case '000 000 rs rt code 110 000' => Trap (TGE (rs, rt))
      case '000 000 rs rt code 110 001' => Trap (TGEU (rs, rt))
      case '000 000 rs rt code 110 010' => Trap (TLT (rs, rt))
      case '000 000 rs rt code 110 011' => Trap (TLTU (rs, rt))
      case '000 000 rs rt code 110 100' => Trap (TEQ (rs, rt))
      case '000 000 rs rt code 110 110' => Trap (TNE (rs, rt))
      case '000 000 00000 rt rd imm5 111 000' => Shift (DSLL (rt, rd, imm5))
      case '000 000 00000 rt rd imm5 111 010' => Shift (DSRL (rt, rd, imm5))
      case '000 000 00000 rt rd imm5 111 011' => Shift (DSRA (rt, rd, imm5))
      case '000 000 00000 rt rd imm5 111 100' => Shift (DSLL32 (rt, rd, imm5))
      case '000 000 00000 rt rd imm5 111 110' => Shift (DSRL32 (rt, rd, imm5))
      case '000 000 00000 rt rd imm5 111 111' => Shift (DSRA32 (rt, rd, imm5))
      case '000 001 rs 00 000 immediate' => Branch (BLTZ (rs, immediate))
      case '000 001 rs 00 001 immediate' => Branch (BGEZ (rs, immediate))
      case '000 001 rs 00 010 immediate' => Branch (BLTZL (rs, immediate))
      case '000 001 rs 00 011 immediate' => Branch (BGEZL (rs, immediate))
      case '000 001 rs 01 000 immediate' => Trap (TGEI (rs, immediate))
      case '000 001 rs 01 001 immediate' => Trap (TGEIU (rs, immediate))
      case '000 001 rs 01 010 immediate' => Trap (TLTI (rs, immediate))
      case '000 001 rs 01 011 immediate' => Trap (TLTIU (rs, immediate))
      case '000 001 rs 01 100 immediate' => Trap (TEQI (rs, immediate))
      case '000 001 rs 01 110 immediate' => Trap (TNEI (rs, immediate))
      case '000 001 11111 10 0 _`2 immediate' => Unpredictable
      case '000 001 rs 10 000 immediate' => Branch (BLTZAL (rs, immediate))
      case '000 001 rs 10 001 immediate' => Branch (BGEZAL (rs, immediate))
      case '000 001 rs 10 010 immediate' => Branch (BLTZALL (rs, immediate))
      case '000 001 rs 10 011 immediate' => Branch (BGEZALL (rs, immediate))
      case '000 010 immediate' => Branch (J (immediate))
      case '000 011 immediate' => Branch (JAL (immediate))
      case '010 000 10000000000000000000 000001' => TLBR
      case '010 000 10000000000000000000 000010' => TLBWI
      case '010 000 10000000000000000000 000110' => TLBWR
      case '010 000 10000000000000000000 001000' => TLBP
      case '010 000 10000000000000000000 011000' => ERET
      case '010 000 00 000 rt rd 00000000 sel' => CP (MFC0 (rt, rd, sel))
      case '010 000 00 001 rt rd 00000000 sel' => CP (DMFC0 (rt, rd, sel))
      case '010 000 00 100 rt rd 00000000 sel' => CP (MTC0 (rt, rd, sel))
      case '010 000 00 101 rt rd 00000000 sel' => CP (DMTC0 (rt, rd, sel))
      case '000 110 rs 00000 immediate' => Branch (BLEZ (rs, immediate))
      case '000 111 rs 00000 immediate' => Branch (BGTZ (rs, immediate))
      case '001 111 00000 rt immediate' => ArithI (LUI (rt, immediate))
      case '010 110 rs 00000 immediate' => Branch (BLEZL (rs, immediate))
      case '010 111 rs 00000 immediate' => Branch (BGTZL (rs, immediate))
      case '011 100 rs rt 00000 00000 000000' => MultDiv (MADD (rs, rt))
      case '011 100 rs rt 00000 00000 000001' => MultDiv (MADDU (rs, rt))
      case '011 100 rs rt 00000 00000 000100' => MultDiv (MSUB (rs, rt))
      case '011 100 rs rt 00000 00000 000101' => MultDiv (MSUBU (rs, rt))
      case '011 100 rs rt rd 00000 000010' => MultDiv (MUL (rs, rt, rd))
      case '000 100 rs rt immediate' => Branch (BEQ (rs, rt, immediate))
      case '000 101 rs rt immediate' => Branch (BNE (rs, rt, immediate))
      case '001 000 rs rt immediate' => ArithI (ADDI (rs, rt, immediate))
      case '001 001 rs rt immediate' => ArithI (ADDIU (rs, rt, immediate))
      case '001 010 rs rt immediate' => ArithI (SLTI (rs, rt, immediate))
      case '001 011 rs rt immediate' => ArithI (SLTIU (rs, rt, immediate))
      case '001 100 rs rt immediate' => ArithI (ANDI (rs, rt, immediate))
      case '001 101 rs rt immediate' => ArithI (ORI (rs, rt, immediate))
      case '001 110 rs rt immediate' => ArithI (XORI (rs, rt, immediate))
      case '010 100 rs rt immediate' => Branch (BEQL (rs, rt, immediate))
      case '010 101 rs rt immediate' => Branch (BNEL (rs, rt, immediate))
      case '011 000 rs rt immediate' => ArithI (DADDI (rs, rt, immediate))
      case '011 001 rs rt immediate' => ArithI (DADDIU (rs, rt, immediate))
      case '011 010 rs rt immediate' => Load (LDL (rs, rt, immediate))
      case '011 011 rs rt immediate' => Load (LDR (rs, rt, immediate))
      case '100 000 rs rt immediate' => Load (LB (rs, rt, immediate))
      case '100 001 rs rt immediate' => Load (LH (rs, rt, immediate))
      case '100 010 rs rt immediate' => Load (LWL (rs, rt, immediate))
      case '100 011 rs rt immediate' => Load (LW (rs, rt, immediate))
      case '100 100 rs rt immediate' => Load (LBU (rs, rt, immediate))
      case '100 101 rs rt immediate' => Load (LHU (rs, rt, immediate))
      case '100 110 rs rt immediate' => Load (LWR (rs, rt, immediate))
      case '100 111 rs rt immediate' => Load (LWU (rs, rt, immediate))
      case '101 000 rs rt immediate' => Store (SB (rs, rt, immediate))
      case '101 001 rs rt immediate' => Store (SH (rs, rt, immediate))
      case '101 010 rs rt immediate' => Store (SWL (rs, rt, immediate))
      case '101 011 rs rt immediate' => Store (SW (rs, rt, immediate))
      case '101 100 rs rt immediate' => Store (SDL (rs, rt, immediate))
      case '101 101 rs rt immediate' => Store (SDR (rs, rt, immediate))
      case '101 110 rs rt immediate' => Store (SWR (rs, rt, immediate))
      case '110 000 rs rt immediate' => Load (LL (rs, rt, immediate))
      case '110 100 rs rt immediate' => Load (LLD (rs, rt, immediate))
      case '110 111 rs rt immediate' => Load (LD (rs, rt, immediate))
      case '111 000 rs rt immediate' => Store (SC (rs, rt, immediate))
      case '111 100 rs rt immediate' => Store (SCD (rs, rt, immediate))
      case '111 111 rs rt immediate' => Store (SD (rs, rt, immediate))
      case '101 111 base opn immediate' => CACHE (base, opn, immediate)
      case '011 111 00000 rt rd 00000 111011' => RDHWR (rt, rd)
      case '010 000 1000 0000 0000 0000 0000 100000' => WAIT
      -- CP2 instructions
      case '010 010 v' => COP2Decode (v) -- coprocessor 2 instructions (0x12)
      case '110 010 v' => LWC2Decode (v) -- coprocessor 2 load word instructions (0x32)
      case '110 110 v' => LDC2Decode (v) -- coprocessor 2 load double instructions (0x36)
      case '111 010 v' => SWC2Decode (v) -- coprocessor 2 store word instructions (0x3a)
      case '111 110 v' => SDC2Decode (v) -- coprocessor 2 store double instructions (0x3e)
      -- reserved instructions
      case _ => ReservedInstruction
   }
}



--================================================
-- The next state function
--================================================

unit Next =
{
   match Fetch
   {
      case Some (w) => Run (Decode (w))
      case None => nothing
   } ;
   match BranchDelay, BranchTo
   {
      case None, None => when not exceptionSignalled do PC <- PC + 4
      case Some (addr), None =>
      {
         BranchDelay <- None;
         PC <- addr
      }
      case None, Some (addr) =>
      {
         BranchDelay <- Some (addr);
         BranchTo <- None;
         PC <- PC + 4
      }
      case _ => #UNPREDICTABLE("Branch follows branch")
   };
   exceptionSignalled <- false;
   CP0.Count <- CP0.Count + 1
}
