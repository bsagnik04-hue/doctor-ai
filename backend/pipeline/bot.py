"""Pipecat SmallWebRTC voice worker. Run: python -m pipeline.bot -t webrtc"""
import os
from datetime import date
from sqlalchemy.orm import joinedload
from dotenv import load_dotenv
from database import SessionLocal
from models import Appointment, Doctor, Slot
from services.appointments import book, cancel

SYSTEM = """You are MediCare AI, a friendly professional hospital receptionist. Help check actual availability, book and cancel appointments. Use the caller's spoken phone number only; do not use browser identity or caller ID. Collect name and phone. Before booking or cancellation, repeat the entire phone number and ask for explicit confirmation. Never invoke a booking/cancellation tool before the caller confirms. Never suggest appointments except actual database slots. Before a booking, confirm doctor, date and time. Only report success after the database tool returns it. If multiple appointments match, ask which appointment, then call cancel with its ID. Never diagnose. Keep speech short and conversational."""
load_dotenv()

try:
    from pipecat.services.llm_service import FunctionCallParams
except ImportError:
    FunctionCallParams = object

async def check_doctor_availability(params: FunctionCallParams, doctor_name: str = "", speciality: str = "", appointment_date: str = ""):
    """Check live availability. Use doctor_name or speciality and optional ISO date."""
    db = SessionLocal()
    try:
        q = db.query(Doctor)
        if doctor_name: q = q.filter(Doctor.name.ilike("%" + doctor_name + "%"))
        if speciality: q = q.filter(Doctor.speciality.ilike("%" + speciality + "%"))
        doctors = q.all(); out=[]
        for d in doctors:
            sq=db.query(Slot).filter_by(doctor_id=d.id,is_booked=False)
            if appointment_date:
                try: sq=sq.filter(Slot.date==date.fromisoformat(appointment_date))
                except ValueError: pass
            slots=sq.order_by(Slot.date,Slot.start_time).all()
            out.append({"doctor_id":d.id,"doctor_name":d.name,"speciality":d.speciality,"experience":d.experience,"fee":d.consultation_fee,"available_slots":[{"date":s.date.isoformat(),"time":s.start_time} for s in slots]})
        await params.result_callback({"doctors":out})
    finally: db.close()

async def book_appointment(params: FunctionCallParams, patient_name: str, patient_phone: str, phone_confirmed: bool, doctor_id: int, appointment_date: str, appointment_time: str):
    """Book an available slot only after repeating and getting confirmation of caller's spoken phone number."""
    if not phone_confirmed:
        await params.result_callback({"error":"Caller must confirm the repeated full phone number before booking."}); return
    db=SessionLocal()
    try:
        try:
            appt=book(db,patient_name,patient_phone,doctor_id,date.fromisoformat(appointment_date),appointment_time)
            d=db.get(Doctor,appt.doctor_id)
            await params.result_callback({"appointment_id":appt.id,"patient_name":appt.patient_name,"doctor":d.name,"speciality":d.speciality,"date":appt.appointment_date.isoformat(),"time":appt.appointment_time,"status":appt.status})
        except (ValueError,TypeError) as e: await params.result_callback({"error":str(e)})
    finally: db.close()

async def cancel_appointment(params: FunctionCallParams, patient_phone: str, phone_confirmed: bool, appointment_id: int = 0):
    """Find and cancel a confirmed appointment after caller confirms spoken phone number. If multiple match, ask which and pass appointment_id."""
    if not phone_confirmed:
        await params.result_callback({"error":"Caller must confirm the repeated full phone number before cancellation."}); return
    db=SessionLocal()
    try:
        try:
            result=cancel(db,patient_phone,appointment_id or None)
            if isinstance(result,dict):
                await params.result_callback({"needs_selection":True,"appointments":[{"appointment_id":a.id,"patient_name":a.patient_name,"doctor":a.doctor.name,"date":a.appointment_date.isoformat(),"time":a.appointment_time} for a in result["appointments"]]})
            else: await params.result_callback({"appointment_id":result.id,"doctor":result.doctor.name,"date":result.appointment_date.isoformat(),"time":result.appointment_time,"status":result.status})
        except ValueError as e: await params.result_callback({"error":str(e)})
    finally: db.close()

async def bot(runner_args):
    from pipecat.frames.frames import LLMRunFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair, LLMUserAggregatorParams
    from pipecat.services.google.llm import GoogleLLMService
    from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
    from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
    from pipecat.workers.runner import WorkerRunner

    required=("GEMINI_API_KEY","ELEVENLABS_API_KEY","ELEVENLABS_VOICE_ID")
    missing=[k for k in required if not os.getenv(k)]
    if missing: raise RuntimeError("Missing voice configuration: " + ", ".join(missing))
    connection: SmallWebRTCConnection = runner_args.webrtc_connection
    transport=SmallWebRTCTransport(webrtc_connection=connection,params=TransportParams(audio_in_enabled=True,audio_out_enabled=True))
    stt=ElevenLabsRealtimeSTTService(api_key=os.environ["ELEVENLABS_API_KEY"])
    llm=GoogleLLMService(api_key=os.environ["GEMINI_API_KEY"],settings=GoogleLLMService.Settings(model="gemini-2.5-flash",system_instruction=SYSTEM))
    tts=ElevenLabsTTSService(api_key=os.environ["ELEVENLABS_API_KEY"],settings=ElevenLabsTTSService.Settings(voice=os.environ["ELEVENLABS_VOICE_ID"],model="eleven_turbo_v2_5"))
    context=LLMContext(tools=[check_doctor_availability,book_appointment,cancel_appointment])
    user,assistant=LLMContextAggregatorPair(context,user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()))
    worker=PipelineWorker(Pipeline([transport.input(),stt,user,llm,tts,transport.output(),assistant]),params=PipelineParams(enable_metrics=True))
    runner=WorkerRunner(handle_sigint=runner_args.handle_sigint)
    await runner.add_workers(worker)
    @transport.event_handler("on_client_connected")
    async def connected(_transport,_client): await worker.queue_frames([LLMRunFrame()])
    @transport.event_handler("on_client_disconnected")
    async def disconnected(_transport,_client): await runner.cancel()
    await runner.run()

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
