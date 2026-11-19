#include "PPECCTVSubsystem.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "TimerManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogPPECCTV, Log, All);

bool UPPECCTVSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
    return FParse::Param(FCommandLine::Get(), TEXT("PPECCTV")) && Super::ShouldCreateSubsystem(Outer);
}

bool UPPECCTVSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UPPECCTVSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    UE_LOG(LogPPECCTV, Log, TEXT("PPE stream: waiting to set the BP_Camera view..."));


    InWorld.GetTimerManager().SetTimer(UpdateTimer, this, &UPPECCTVSubsystem::Update, 0.25f, true, 0.5f);
}

void UPPECCTVSubsystem::Deinitialize()
{
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(UpdateTimer);
    }
    Super::Deinitialize();
}

void UPPECCTVSubsystem::Update()
{
    UWorld* World = GetWorld();
    APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
    if (!PC || bFailed)
    {
        return;
    }
    if (!Camera.IsValid() && !SpawnCamera())
    {
        return;
    }
    if (PC->GetViewTarget() != Camera.Get())
    {
        PC->SetViewTarget(Camera.Get());
    }
}

bool UPPECCTVSubsystem::SpawnCamera()
{
    UWorld* World = GetWorld();
    TArray<AActor*> Found;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetClass()->GetName().StartsWith(TEXT("BP_Camera_C")))
        {
            Found.Add(*It);
        }
    }
    if (Found.Num() != 1)
    {
        UE_LOG(LogPPECCTV, Error, TEXT("PPE stream CCTV setup failed: expected exactly one BP_Camera, found %d"), Found.Num());
        bFailed = true;
        return false;
    }
    USceneCaptureComponent2D* Capture = Found[0]->FindComponentByClass<USceneCaptureComponent2D>();
    if (!Capture)
    {
        UE_LOG(LogPPECCTV, Error, TEXT("PPE stream CCTV setup failed: BP_Camera has no SceneCaptureComponent2D"));
        bFailed = true;
        return false;
    }

    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Params.ObjectFlags |= RF_Transient;
    ACameraActor* Cam = World->SpawnActor<ACameraActor>(Capture->GetComponentLocation(),
                                                        Capture->GetComponentRotation(), Params);
    if (!Cam)
    {
        return false;
    }
    Cam->SetOwner(Found[0]);
    if (!Cam->AttachToComponent(Capture, FAttachmentTransformRules::SnapToTargetNotIncludingScale))
    {
        UE_LOG(LogPPECCTV, Error, TEXT("PPE stream CCTV setup failed: could not attach the view camera to BP_Camera's scene capture"));
        Cam->Destroy();
        bFailed = true;
        return false;
    }
    UCameraComponent* Comp = Cam->GetCameraComponent();
    Comp->SetFieldOfView(Capture->FOVAngle);
    if (const UTextureRenderTarget2D* Target = Capture->TextureTarget)
    {
        Comp->SetAspectRatio(float(Target->SizeX) / float(Target->SizeY));
        Comp->SetConstraintAspectRatio(true);
    }
    Comp->PostProcessSettings = Capture->PostProcessSettings;
    Comp->PostProcessBlendWeight = Capture->PostProcessBlendWeight;
    Camera = Cam;
    UE_LOG(LogPPECCTV, Log, TEXT("PPE_STREAM_CCTV_READY fov=%.1f camera=%s attached_to=%s"),
        Capture->FOVAngle, *Found[0]->GetName(), *Capture->GetName());
    return true;
}
