#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "PPECCTVSubsystem.generated.h"

class ACameraActor;







UCLASS()
class PPEWORKERS_API UPPECCTVSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;

protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
    void Update();
    bool SpawnCamera();

    TWeakObjectPtr<ACameraActor> Camera;
    FTimerHandle UpdateTimer;
    bool bFailed = false;
};
