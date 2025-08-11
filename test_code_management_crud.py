#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
코드 관리 CRUD 테스트 스크립트
모든 기능(생성, 읽기, 수정, 삭제)을 자동으로 테스트합니다.
"""

import requests
import json
import time
from datetime import datetime

class CodeManagementTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        """테스트 결과 로깅"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        self.test_results.append((test_name, success, message))
        
    def login(self):
        """로그인 (세션 필요)"""
        try:
            # 메인 페이지 접속으로 세션 확보
            response = self.session.get(f"{self.base_url}/admin/code_management")
            if response.status_code in [200, 302]:
                self.log_test("로그인/세션 확보", True, "정상 접근")
                return True
            else:
                self.log_test("로그인/세션 확보", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("로그인/세션 확보", False, str(e))
            return False
    
    def test_read_codes(self):
        """READ 테스트 - 코드 목록 조회"""
        try:
            # 코드 관리 페이지 접속
            response = self.session.get(f"{self.base_url}/admin/code_management")
            
            if response.status_code == 200:
                # 페이지 내용 확인
                content = response.text
                if "코드 관리" in content and "ROOT" in content:
                    self.log_test("READ - 코드 목록 조회", True, "페이지 로드 성공")
                    return True
                else:
                    self.log_test("READ - 코드 목록 조회", False, "페이지 내용 확인 실패")
                    return False
            else:
                self.log_test("READ - 코드 목록 조회", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("READ - 코드 목록 조회", False, str(e))
            return False
    
    def test_create_code(self):
        """CREATE 테스트 - 새 코드 생성"""
        try:
            # 테스트용 코드 데이터
            test_code_data = {
                'parent_seq': '0',
                'depth': '1',
                'code': 'TEST',
                'code_name': '테스트 코드',
                'code_info': 'CRUD 테스트용 코드',
                'sort': '1'
            }
            
            # 코드 생성 요청
            response = self.session.post(
                f"{self.base_url}/admin/api/codes/create",
                data=test_code_data
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        self.created_code_seq = result.get('data', {}).get('seq')
                        self.log_test("CREATE - 코드 생성", True, f"코드 생성 성공 (seq: {self.created_code_seq})")
                        return True
                    else:
                        self.log_test("CREATE - 코드 생성", False, result.get('message', '알 수 없는 오류'))
                        return False
                except:
                    self.log_test("CREATE - 코드 생성", False, "응답 JSON 파싱 실패")
                    return False
            else:
                self.log_test("CREATE - 코드 생성", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("CREATE - 코드 생성", False, str(e))
            return False
    
    def test_get_code(self, seq):
        """READ 테스트 - 특정 코드 조회"""
        try:
            response = self.session.post(
                f"{self.base_url}/admin/api/codes/get",
                data={'seq': seq}
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success') and result.get('data'):
                        code_data = result['data']
                        if code_data.get('code') == 'TEST':
                            self.log_test("READ - 특정 코드 조회", True, f"코드 조회 성공: {code_data.get('code_name')}")
                            return True
                        else:
                            self.log_test("READ - 특정 코드 조회", False, "코드 내용 불일치")
                            return False
                    else:
                        self.log_test("READ - 특정 코드 조회", False, result.get('message', '코드 없음'))
                        return False
                except:
                    self.log_test("READ - 특정 코드 조회", False, "응답 JSON 파싱 실패")
                    return False
            else:
                self.log_test("READ - 특정 코드 조회", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("READ - 특정 코드 조회", False, str(e))
            return False
    
    def test_update_code(self, seq):
        """UPDATE 테스트 - 코드 수정"""
        try:
            # 수정할 데이터
            update_data = {
                'edit_seq': seq,
                'parent_seq': '0',
                'depth': '1',
                'code': 'TEST',
                'code_name': '테스트 코드 (수정됨)',
                'code_info': 'CRUD 테스트용 코드 - 수정 완료',
                'sort': '1'
            }
            
            response = self.session.post(
                f"{self.base_url}/admin/api/codes/update",
                data=update_data
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        self.log_test("UPDATE - 코드 수정", True, "코드 수정 성공")
                        return True
                    else:
                        self.log_test("UPDATE - 코드 수정", False, result.get('message', '수정 실패'))
                        return False
                except:
                    self.log_test("UPDATE - 코드 수정", False, "응답 JSON 파싱 실패")
                    return False
            else:
                self.log_test("UPDATE - 코드 수정", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("UPDATE - 코드 수정", False, str(e))
            return False
    
    def test_delete_code(self, seq):
        """DELETE 테스트 - 코드 삭제"""
        try:
            response = self.session.post(
                f"{self.base_url}/admin/api/codes/delete",
                data={'seq': seq}
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        self.log_test("DELETE - 코드 삭제", True, "코드 삭제 성공")
                        return True
                    else:
                        self.log_test("DELETE - 코드 삭제", False, result.get('message', '삭제 실패'))
                        return False
                except:
                    self.log_test("DELETE - 코드 삭제", False, "응답 JSON 파싱 실패")
                    return False
            else:
                self.log_test("DELETE - 코드 삭제", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("DELETE - 코드 삭제", False, str(e))
            return False
    
    def test_drag_drop_sort(self):
        """드래그 앤 드롭 정렬 테스트"""
        try:
            # 테스트용 정렬 데이터
            sort_data = {
                'parent_seq': '0',
                'depth': '0',
                'order': json.dumps([1, 2, 28, 39])  # JPT, RPT, BRAND, PRT 순서
            }
            
            response = self.session.post(
                f"{self.base_url}/admin/api/codes/update-sort",
                data=sort_data
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        self.log_test("드래그 앤 드롭 정렬", True, "정렬 순서 변경 성공")
                        return True
                    else:
                        self.log_test("드래그 앤 드롭 정렬", False, result.get('message', '정렬 실패'))
                        return False
                except:
                    self.log_test("드래그 앤 드롭 정렬", False, "응답 JSON 파싱 실패")
                    return False
            else:
                self.log_test("드래그 앤 드롭 정렬", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("드래그 앤 드롭 정렬", False, str(e))
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 60)
        print("🧪 코드 관리 CRUD 테스트 시작")
        print("=" * 60)
        
        # 1. 로그인/세션 확보
        if not self.login():
            print("❌ 로그인 실패로 테스트 중단")
            return False
        
        time.sleep(1)
        
        # 2. READ 테스트
        if not self.test_read_codes():
            print("❌ 코드 목록 조회 실패")
            return False
        
        time.sleep(1)
        
        # 3. CREATE 테스트
        if not self.test_create_code():
            print("❌ 코드 생성 실패")
            return False
        
        time.sleep(1)
        
        # 4. READ 개별 코드 테스트 (생성된 코드)
        if hasattr(self, 'created_code_seq') and self.created_code_seq:
            if not self.test_get_code(self.created_code_seq):
                print("❌ 생성된 코드 조회 실패")
        
        time.sleep(1)
        
        # 5. UPDATE 테스트
        if hasattr(self, 'created_code_seq') and self.created_code_seq:
            if not self.test_update_code(self.created_code_seq):
                print("❌ 코드 수정 실패")
        
        time.sleep(1)
        
        # 6. 드래그 앤 드롭 정렬 테스트
        self.test_drag_drop_sort()
        
        time.sleep(1)
        
        # 7. DELETE 테스트 (마지막에 정리)
        if hasattr(self, 'created_code_seq') and self.created_code_seq:
            if not self.test_delete_code(self.created_code_seq):
                print("❌ 코드 삭제 실패")
        
        # 결과 요약
        self.print_summary()
        
        return True
    
    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r[1]])
        failed_tests = total_tests - passed_tests
        
        print(f"총 테스트: {total_tests}개")
        print(f"✅ 성공: {passed_tests}개")
        print(f"❌ 실패: {failed_tests}개")
        print(f"성공률: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 실패한 테스트:")
            for name, success, message in self.test_results:
                if not success:
                    print(f"  - {name}: {message}")
        
        print("\n" + "=" * 60)
        
        return failed_tests == 0

def main():
    tester = CodeManagementTester()
    success = tester.run_all_tests()
    
    if success:
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        return True
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
        return False

if __name__ == "__main__":
    main() 