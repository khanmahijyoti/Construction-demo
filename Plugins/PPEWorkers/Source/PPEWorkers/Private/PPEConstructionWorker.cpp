#include "PPEConstructionWorker.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

APPEConstructionWorker::APPEConstructionWorker()
{
    PrimaryActorTick.bCanEverTick = false;
    GetCapsuleComponent()->InitCapsuleSize(34.f,88.f);
    GetMesh()->SetRelativeLocation(FVector(0,0,-88));
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    auto MakePart = [this](FName Name)
    {
        auto* Part = CreateDefaultSubobject<USkeletalMeshComponent>(Name);
        Part->SetupAttachment(GetMesh());
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        return Part;
    };
    Shirt=MakePart(TEXT("Shirt")); Pants=MakePart(TEXT("Pants")); Boots=MakePart(TEXT("Boots"));
    SafetyVest=MakePart(TEXT("SafetyVest")); CasualVest=MakePart(TEXT("CasualVest"));
    Helmet=MakePart(TEXT("Helmet")); Beard=MakePart(TEXT("Beard")); Eyelashes=MakePart(TEXT("Eyelashes"));
    Scalp=MakePart(TEXT("Scalp")); Hair=MakePart(TEXT("Hair"));
}
void APPEConstructionWorker::SetPart(USkeletalMeshComponent* Part, USkeletalMesh* Asset, bool Visible)
{
    Part->SetSkeletalMeshAsset(Asset);
    Part->SetLeaderPoseComponent(GetMesh(),true,false);
    Part->SetVisibility(Visible);
    Part->SetHiddenInGame(!Visible);
}
void APPEConstructionWorker::SetTint(USkeletalMeshComponent* Part,int32 Slot,UMaterialInterface* Material,const FLinearColor& Tint)
{
    if(!Material) return;
    UMaterialInstanceDynamic* Instance=UMaterialInstanceDynamic::Create(Material,this);
    Instance->SetVectorParameterValue(TEXT("Tint"),Tint);
    Part->SetMaterial(Slot,Instance);
}
void APPEConstructionWorker::ApplyAppearance()
{
    GetMesh()->SetSkeletalMeshAsset(BodyAsset);
    SetPart(Shirt,ShirtAsset,true); SetPart(Pants,PantsAsset,true); SetPart(Boots,BootsAsset,true);
    SetPart(SafetyVest,SafetyVestAsset,WearSafetyVest); SetPart(CasualVest,CasualVestAsset,!WearSafetyVest);
    SetPart(Helmet,HelmetAsset,WearHelmet); SetPart(Beard,BeardAsset,HasBeard);
    SetPart(Eyelashes,EyelashesAsset,true); SetPart(Scalp,ScalpAsset,!WearHelmet); SetPart(Hair,HairAsset,!WearHelmet);
    if(AtlasMaterial) { GetMesh()->SetMaterial(0,AtlasMaterial); Boots->SetMaterial(0,AtlasMaterial); }
    SetTint(GetMesh(),1,SkinMaterial,SkinTint); SetTint(Scalp,0,SkinMaterial,SkinTint);
    SetTint(Shirt,0,ClothMaterial,ShirtColor); SetTint(Pants,0,ClothMaterial,PantsColor);
    SetTint(CasualVest,0,PlainClothMaterial,CasualVestColor);
    SetTint(Helmet,0,HardhatMaterial,HelmetColor);
    if(BeardMaterial) { Beard->SetMaterial(0,BeardMaterial); Eyelashes->SetMaterial(0,BeardMaterial); }
    if(HairMaterial) Hair->SetMaterial(0,HairMaterial);
    if(UMaterialInterface* Material=YellowSafetyVest ? YellowVestMaterial.Get() : OrangeVestMaterial.Get()) SafetyVest->SetMaterial(0,Material);
    GetMesh()->OverrideAnimationData(Animate ? AnimationClip.Get() : nullptr,true,Animate,AnimationOffset,AnimationRate);
}
void APPEConstructionWorker::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    ApplyAppearance();
}
void APPEConstructionWorker::BeginPlay()
{
    Super::BeginPlay();
    ApplyAppearance();
}
