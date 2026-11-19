#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "PPEConstructionWorker.generated.h"

class USkeletalMesh;
class USkeletalMeshComponent;
class UMaterialInterface;
class UAnimSequence;

UCLASS(Blueprintable)
class PPEWORKERS_API APPEConstructionWorker : public ACharacter
{
    GENERATED_BODY()
public:
    APPEConstructionWorker();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Equipment") bool WearHelmet = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Equipment") bool WearSafetyVest = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Equipment") bool YellowSafetyVest = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Appearance") bool HasBeard = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Appearance") FLinearColor SkinTint = FLinearColor::White;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Appearance") FLinearColor HelmetColor = FLinearColor(.8f,.8f,.8f,1.f);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Appearance") FLinearColor ShirtColor = FLinearColor(.025f,.04f,.065f,1.f);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Appearance") FLinearColor PantsColor = FLinearColor(.12f,.09f,.055f,1.f);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Appearance") FLinearColor CasualVestColor = FLinearColor(.25f,.16f,.08f,1.f);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Animation") bool Animate = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Animation",meta=(ClampMin="0.1",ClampMax="3.0")) float AnimationRate = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Animation",meta=(ClampMin="0.0")) float AnimationOffset = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Worker|Animation") TObjectPtr<UAnimSequence> AnimationClip;

    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> BodyAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> ShirtAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> PantsAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> BootsAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> SafetyVestAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> CasualVestAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> HelmetAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> BeardAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> EyelashesAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> ScalpAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Assets") TObjectPtr<USkeletalMesh> HairAsset;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> AtlasMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> SkinMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> ClothMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> PlainClothMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> OrangeVestMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> YellowVestMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> HardhatMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> BeardMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Worker|Materials") TObjectPtr<UMaterialInterface> HairMaterial;

    UFUNCTION(BlueprintCallable, CallInEditor, Category="Worker") void ApplyAppearance();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> Shirt;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> Pants;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> Boots;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> SafetyVest;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> CasualVest;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> Helmet;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> Beard;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> Eyelashes;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> Scalp;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Worker|Components") TObjectPtr<USkeletalMeshComponent> Hair;
private:
    void SetPart(USkeletalMeshComponent* Part, USkeletalMesh* Asset, bool Visible);
    void SetTint(USkeletalMeshComponent* Part, int32 Slot, UMaterialInterface* Material, const FLinearColor& Tint);
};
