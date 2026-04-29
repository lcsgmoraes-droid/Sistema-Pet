import React from 'react';
import { Platform, type ScrollViewProps } from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';

type Props = ScrollViewProps & {
  children: React.ReactNode;
  enableAutomaticScroll?: boolean;
  enableOnAndroid?: boolean;
  extraHeight?: number;
  extraScrollHeight?: number;
  keyboardOpeningTime?: number;
};

export default function KeyboardSafeScrollView({
  children,
  enableAutomaticScroll = true,
  enableOnAndroid = true,
  extraHeight = Platform.OS === 'android' ? 140 : 90,
  extraScrollHeight = Platform.OS === 'android' ? 96 : 24,
  keyboardOpeningTime = 0,
  keyboardShouldPersistTaps = 'handled',
  showsVerticalScrollIndicator = false,
  ...props
}: Props) {
  return (
    <KeyboardAwareScrollView
      enableAutomaticScroll={enableAutomaticScroll}
      enableOnAndroid={enableOnAndroid}
      extraHeight={extraHeight}
      extraScrollHeight={extraScrollHeight}
      keyboardOpeningTime={keyboardOpeningTime}
      keyboardShouldPersistTaps={keyboardShouldPersistTaps}
      showsVerticalScrollIndicator={showsVerticalScrollIndicator}
      {...props}
    >
      {children}
    </KeyboardAwareScrollView>
  );
}
